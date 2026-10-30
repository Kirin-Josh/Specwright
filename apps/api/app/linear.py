"""Thin client for Linear's GraphQL API — only the calls the sync stage needs."""

from dataclasses import dataclass
from typing import Any

import httpx

API_URL = "https://api.linear.app/graphql"


class LinearError(Exception):
    pass


@dataclass
class Team:
    id: str
    name: str
    estimation_type: str  # notUsed | exponential | fibonacci | linear | tShirt


class LinearClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        if not api_key:
            raise LinearError("LINEAR_API_KEY is not set")
        # Personal API keys go in the header as-is, without "Bearer".
        self.http = http or httpx.Client(headers={"Authorization": api_key}, timeout=30)

    def _gql(self, query: str, **variables: Any) -> dict[str, Any]:
        res = self.http.post(API_URL, json={"query": query, "variables": variables})
        try:
            body = res.json()
        except ValueError:
            res.raise_for_status()
            raise
        if body.get("errors"):
            raise LinearError("; ".join(e.get("message", str(e)) for e in body["errors"]))
        res.raise_for_status()
        return body["data"]

    def find_team(self, key: str) -> Team | None:
        data = self._gql(
            "query($key: String!) { teams(filter: {key: {eq: $key}}) "
            "{ nodes { id name issueEstimationType } } }",
            key=key,
        )
        nodes = data["teams"]["nodes"]
        if not nodes:
            return None
        n = nodes[0]
        return Team(id=n["id"], name=n["name"], estimation_type=n["issueEstimationType"])

    def find_label(self, team_id: str, name: str) -> str | None:
        """A label with this name usable by the team: the team's own or a workspace label."""
        data = self._gql(
            "query($name: String!) { issueLabels(filter: {name: {eqIgnoreCase: $name}}) "
            "{ nodes { id isGroup team { id } } } }",
            name=name,
        )
        for n in data["issueLabels"]["nodes"]:
            if not n["isGroup"] and (n["team"] is None or n["team"]["id"] == team_id):
                return n["id"]
        return None

    def create_label(self, team_id: str, name: str, color: str) -> str:
        data = self._gql(
            "mutation($input: IssueLabelCreateInput!) "
            "{ issueLabelCreate(input: $input) { issueLabel { id } } }",
            input={"teamId": team_id, "name": name, "color": color},
        )
        return data["issueLabelCreate"]["issueLabel"]["id"]

    def create_project(self, team_id: str, name: str, description: str) -> tuple[str, str]:
        data = self._gql(
            "mutation($input: ProjectCreateInput!) "
            "{ projectCreate(input: $input) { project { id url } } }",
            input={"teamIds": [team_id], "name": name, "description": description},
        )
        project = data["projectCreate"]["project"]
        return project["id"], project["url"]

    def update_project(self, project_id: str, name: str, description: str) -> str:
        data = self._gql(
            "mutation($id: String!, $input: ProjectUpdateInput!) "
            "{ projectUpdate(id: $id, input: $input) { project { url } } }",
            id=project_id, input={"name": name, "description": description},
        )
        return data["projectUpdate"]["project"]["url"]

    def create_milestone(self, project_id: str, name: str, description: str) -> str:
        data = self._gql(
            "mutation($input: ProjectMilestoneCreateInput!) "
            "{ projectMilestoneCreate(input: $input) { projectMilestone { id } } }",
            input={"projectId": project_id, "name": name, "description": description},
        )
        return data["projectMilestoneCreate"]["projectMilestone"]["id"]

    def update_milestone(self, milestone_id: str, name: str, description: str) -> None:
        self._gql(
            "mutation($id: String!, $input: ProjectMilestoneUpdateInput!) "
            "{ projectMilestoneUpdate(id: $id, input: $input) { success } }",
            id=milestone_id, input={"name": name, "description": description},
        )

    def create_issue(self, fields: dict[str, Any]) -> str:
        data = self._gql(
            "mutation($input: IssueCreateInput!) { issueCreate(input: $input) { issue { id } } }",
            input=fields,
        )
        return data["issueCreate"]["issue"]["id"]

    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> None:
        self._gql(
            "mutation($id: String!, $input: IssueUpdateInput!) "
            "{ issueUpdate(id: $id, input: $input) { success } }",
            id=issue_id, input=fields,
        )

    def create_relation(self, blocking_issue_id: str, blocked_issue_id: str) -> None:
        self._gql(
            "mutation($input: IssueRelationCreateInput!) "
            "{ issueRelationCreate(input: $input) { success } }",
            input={"issueId": blocking_issue_id, "relatedIssueId": blocked_issue_id,
                   "type": "blocks"},
        )
