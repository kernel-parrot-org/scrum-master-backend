import httpx


class JiraClient:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def get_users(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/rest/api/2/user/search",
                params={"username": ".", "maxResults": 1000},
                headers=self.headers
            )
        r.raise_for_status()
        return r.json()

    async def get_boards(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/rest/agile/1.0/board",
                headers=self.headers
            )
        r.raise_for_status()
        return r.json().get("values", [])

    async def get_board_issues(self, board_id: int) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/rest/agile/1.0/board/{board_id}/issue",
                params={"maxResults": 1000},
                headers=self.headers,
            )
        r.raise_for_status()
        return r.json().get("issues", [])

    async def create_issue(self, payload: dict) -> dict:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[JIRA CLIENT] Creating issue with payload: {payload}")
        
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.url}/rest/api/2/issue",
                json=payload,
                headers=self.headers
            )
        
        if r.status_code != 201:
            logger.error(f"[JIRA CLIENT] Failed to create issue. Status: {r.status_code}, Response: {r.text}")
        
        r.raise_for_status()
        return r.json()

    async def update_issue(self, issue_key: str, fields: dict):
        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{self.url}/rest/api/2/issue/{issue_key}",
                json={"fields": fields},
                headers=self.headers
            )
        r.raise_for_status()
        return {"status": "updated"}

    async def delete_issue(self, issue_key: str):
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{self.url}/rest/api/2/issue/{issue_key}",
                headers=self.headers
            )
        r.raise_for_status()
        return {"status": "deleted"}
