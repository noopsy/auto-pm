import os
import time
from typing import Dict, List, Optional, Union
import requests
from datetime import datetime

class GitHubIssueReader:
    """
    A class to handle reading issues from GitHub repositories for Claude MCP integration.
    """
    
    def __init__(self, token: str = None):
        """
        Initialize the GitHub issue reader with authentication token.
        
        Args:
            token (str): GitHub Personal Access Token. If not provided, will look for GITHUB_TOKEN env variable.
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token is required. Provide it directly or set GITHUB_TOKEN environment variable.")
        
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Claude-MCP-GitHub-Integration"
        })
        
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle GitHub API rate limiting with exponential backoff."""
        if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers['X-RateLimit-Remaining'])
            if remaining == 0:
                reset_time = int(response.headers['X-RateLimit-Reset'])
                sleep_time = reset_time - int(time.time()) + 1
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 3600))  # Cap at 1 hour
                    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an HTTP request with rate limit handling and error checking."""
        while True:
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code == 200:
                return response
            
            if response.status_code == 403:
                self._handle_rate_limit(response)
                continue
                
            response.raise_for_status()
            
    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict:
        """
        Fetch a single issue by its number.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            issue_number (int): Issue number
            
        Returns:
            Dict: Issue data
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self._make_request('GET', url)
        return response.json()
        
    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = 'open',
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        creator: Optional[str] = None,
        mentioned: Optional[str] = None,
        since: Optional[Union[str, datetime]] = None,
        per_page: int = 30,
        page: int = 1
    ) -> List[Dict]:
        """
        List issues in a repository with filtering options.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            state (str): Issue state ('open', 'closed', 'all')
            labels (List[str], optional): List of label names
            assignee (str, optional): Username of assignee
            creator (str, optional): Username of issue creator
            mentioned (str, optional): Username mentioned in issue
            since (Union[str, datetime], optional): Only issues updated after this time
            per_page (int): Number of results per page (max 100)
            page (int): Page number for pagination
            
        Returns:
            List[Dict]: List of issue data
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        
        params = {
            'state': state,
            'per_page': min(per_page, 100),
            'page': page
        }
        
        if labels:
            params['labels'] = ','.join(labels)
        if assignee:
            params['assignee'] = assignee
        if creator:
            params['creator'] = creator
        if mentioned:
            params['mentioned'] = mentioned
        if since:
            if isinstance(since, datetime):
                since = since.isoformat()
            params['since'] = since
            
        response = self._make_request('GET', url, params=params)
        return response.json()
        
    def get_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        per_page: int = 30,
        page: int = 1
    ) -> List[Dict]:
        """
        Get comments for a specific issue.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            issue_number (int): Issue number
            per_page (int): Number of results per page (max 100)
            page (int): Page number for pagination
            
        Returns:
            List[Dict]: List of comment data
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        
        params = {
            'per_page': min(per_page, 100),
            'page': page
        }
        
        response = self._make_request('GET', url, params=params)
        return response.json()

# Example Claude MCP function implementation
def mcp_get_issue(owner: str, repo: str, issue_number: int) -> Dict:
    """
    MCP function to get a single GitHub issue.
    
    Args:
        owner (str): Repository owner
        repo (str): Repository name
        issue_number (int): Issue number
        
    Returns:
        Dict: Formatted issue data for Claude MCP
    """
    reader = GitHubIssueReader()
    issue_data = reader.get_issue(owner, repo, issue_number)
    
    # Transform data into MCP-friendly format
    return {
        'title': issue_data['title'],
        'body': issue_data['body'],
        'state': issue_data['state'],
        'number': issue_data['number'],
        'created_at': issue_data['created_at'],
        'updated_at': issue_data['updated_at'],
        'labels': [label['name'] for label in issue_data['labels']],
        'assignees': [assignee['login'] for assignee in issue_data['assignees']],
        'comments_count': issue_data['comments'],
        'url': issue_data['html_url']
    }

# Example Claude MCP function implementation
def mcp_list_issues(
    owner: str,
    repo: str,
    state: str = 'open',
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    per_page: int = 30,
    page: int = 1
) -> List[Dict]:
    """
    MCP function to list GitHub issues with filtering.
    
    Args:
        owner (str): Repository owner
        repo (str): Repository name
        state (str): Issue state
        labels (List[str], optional): List of label names
        assignee (str, optional): Username of assignee
        per_page (int): Results per page
        page (int): Page number
        
    Returns:
        List[Dict]: List of formatted issue data for Claude MCP
    """
    reader = GitHubIssueReader()
    issues_data = reader.list_issues(
        owner=owner,
        repo=repo,
        state=state,
        labels=labels,
        assignee=assignee,
        per_page=per_page,
        page=page
    )
    
    # Transform data into MCP-friendly format
    return [{
        'title': issue['title'],
        'body': issue['body'],
        'state': issue['state'],
        'number': issue['number'],
        'created_at': issue['created_at'],
        'updated_at': issue['updated_at'],
        'labels': [label['name'] for label in issue['labels']],
        'assignees': [assignee['login'] for assignee in issue['assignees']],
        'comments_count': issue['comments'],
        'url': issue['html_url']
    } for issue in issues_data]