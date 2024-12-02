import { z } from "zod";
import { Octokit } from "@octokit/rest";
import { McpFunction, McpFunctionContext } from "../types";
import { RepoReference } from "./schemas";

// Schema Definitions
export const GetIssueParams = z.object({
  ...RepoReference.shape,
  issueNumber: z.number().int().positive(),
});

export const ListIssuesParams = z.object({
  ...RepoReference.shape,
  state: z.enum(["open", "closed", "all"]).optional().default("open"),
  labels: z.array(z.string()).optional(),
  assignee: z.string().optional(),
  creator: z.string().optional(),
  mentioned: z.string().optional(),
  since: z.string().optional(), // ISO 8601 timestamp
  perPage: z.number().int().min(1).max(100).optional().default(30),
  page: z.number().int().min(1).optional().default(1),
});

export const IssueLabel = z.object({
  name: z.string(),
  color: z.string(),
  description: z.string().nullable(),
});

export const IssueUser = z.object({
  login: z.string(),
  id: z.number(),
  avatar_url: z.string(),
  url: z.string(),
});

export const Issue = z.object({
  number: z.number(),
  title: z.string(),
  body: z.string().nullable(),
  state: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  closed_at: z.string().nullable(),
  labels: z.array(IssueLabel),
  assignees: z.array(IssueUser),
  comments: z.number(),
  html_url: z.string(),
  user: IssueUser,
});

// Function Implementations
export const getIssue: McpFunction<typeof GetIssueParams> = async (
  params,
  context: McpFunctionContext
) => {
  const { owner, repo, issueNumber } = GetIssueParams.parse(params);
  const octokit = new Octokit({ auth: context.githubToken });

  try {
    const response = await octokit.issues.get({
      owner,
      repo,
      issue_number: issueNumber,
    });

    return Issue.parse(response.data);
  } catch (error) {
    if (error.status === 404) {
      throw new Error(`Issue #${issueNumber} not found in ${owner}/${repo}`);
    }
    throw error;
  }
};

export const listIssues: McpFunction<typeof ListIssuesParams> = async (
  params,
  context: McpFunctionContext
) => {
  const {
    owner,
    repo,
    state,
    labels,
    assignee,
    creator,
    mentioned,
    since,
    perPage,
    page,
  } = ListIssuesParams.parse(params);

  const octokit = new Octokit({ auth: context.githubToken });

  try {
    const response = await octokit.issues.listForRepo({
      owner,
      repo,
      state,
      labels: labels?.join(","),
      assignee,
      creator,
      mentioned,
      since,
      per_page: perPage,
      page,
    });

    return z.array(Issue).parse(response.data);
  } catch (error) {
    if (error.status === 404) {
      throw new Error(`Repository ${owner}/${repo} not found`);
    }
    throw error;
  }
};

// MCP Function Registration
export const issueReaderFunctions = {
  getIssue: {
    parameters: GetIssueParams,
    handler: getIssue,
    description: "Get a single GitHub issue by number",
  },
  listIssues: {
    parameters: ListIssuesParams,
    handler: listIssues,
    description: "List GitHub issues with filtering options",
  },
} as const;

// Function Export for index.ts integration
export function registerIssueReaderFunctions(
  functions: Record<string, McpFunction<any>>
) {
  Object.entries(issueReaderFunctions).forEach(([name, fn]) => {
    functions[`github_${name}`] = fn;
  });
}