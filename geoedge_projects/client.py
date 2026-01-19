from __future__ import annotations

import os
import time
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 30


class TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that sets a default timeout for requests."""
    def __init__(self, *args, timeout: int = DEFAULT_TIMEOUT, **kwargs):
        self._timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout", self._timeout)
        kwargs["timeout"] = timeout
        return super().send(request, **kwargs)


class GeoEdgeClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
    ):
        self.api_key = api_key or os.getenv("GEOEDGE_API_KEY")
        self.base_url = (base_url or os.getenv("GEOEDGE_API_BASE") or "").rstrip("/")
        if not self.api_key:
            raise RuntimeError("GEOEDGE_API_KEY is required (set in environment or .env).")
        if not self.base_url:
            raise RuntimeError("GEOEDGE_API_BASE is required (set in environment or .env).")

        self.session = requests.Session()
        self.session.headers.update({"Authorization": self.api_key})

        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            raise_on_status=False,
        )
        adapter = TimeoutHTTPAdapter(timeout=timeout, max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # -------------------------------
    # Low-level request helper
    # -------------------------------
    def _request(self, method: str, path_or_url: str, *, params=None, data=None) -> dict:
        # Allow absolute "next_page" URLs returned by API or relative paths
        url = path_or_url
        if not path_or_url.lower().startswith(("http://", "https://")):
            url = f"{self.base_url}{path_or_url}"
        resp = self.session.request(method, url, params=params, data=data)
        # GeoEdge sometimes returns JSON with HTTP error codes; try to parse either way
        try:
            payload = resp.json()
        except ValueError:
            resp.raise_for_status()
            return {}
        # If non-2xx and payload has status -> raise a helpful error
        if not resp.ok and isinstance(payload, dict) and "status" in payload:
            msg = payload["status"]
            raise requests.HTTPError(f"GeoEdge API error: {msg}", response=resp)
        # For explicit non-OK without status JSON
        resp.raise_for_status()
        return payload

    # -------------------------------
    # API methods (subset we need)
    # -------------------------------
    def iter_projects_list(
        self, *, limit: int = 1000, offset: int = 0
    ) -> Iterable[Dict[str, Any]]:
        """Iterate over projects from /projects (list). Does NOT include locations."""
        if limit < 1 or limit > 50000:
            raise ValueError("limit must be between 1 and 50000")

        next_path = f"/projects?offset={offset}&limit={limit}"
        while next_path:
            data = self._request("GET", next_path)
            projects = data.get("projects", [])
            for p in projects:
                yield p
            next_page = data.get("next_page")  # absolute URL or None
            next_path = None
            if next_page:
                # Keep using the absolute next_page to avoid reconstructing params
                parsed = urlparse(next_page)
                next_path = next_page if parsed.scheme in ("http", "https") else parsed.path

    def get_project(self, project_id: str) -> dict:
        data = self._request("GET", f"/projects/{project_id}")
        # API response structure: {"response": {"project": {...}}, "status": {...}}
        response = data.get("response", {})
        return response.get("project", {})

    def list_alert_trigger_types(self) -> Dict[str, Dict[str, str]]:
        data = self._request("GET", "/alerts/trigger-types")
        items = data.get("trigger-types") or data.get("trigger_types") or []
        mapping: Dict[str, Dict[str, str]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            trigger_id = item.get("id")
            trigger_id = str(trigger_id) if trigger_id is not None else None
            if not trigger_id:
                continue
            mapping[trigger_id] = {
                "key": item.get("key", ""),
                "description": item.get("description", ""),
            }
        return mapping

    def iter_alerts_history(
        self,
        *,
        project_id: Optional[str] = None,
        alert_id: Optional[str] = None,
        trigger_type_id: Optional[str] = None,
        min_datetime: Optional[str] = None,
        max_datetime: Optional[str] = None,
        location_id: Optional[str] = None,
        full_raw: Optional[int] = None,
        page_limit: int = 500,
        max_pages: Optional[int] = None,
    ) -> Iterable[Dict[str, Any]]:

        params: Dict[str, str] = {}
        if project_id:
            params["project_id"] = project_id
        if alert_id:
            params["alert_id"] = alert_id
        if trigger_type_id:
            params["trigger_type_id"] = str(trigger_type_id)
        if min_datetime:
            params["min_datetime"] = min_datetime
        if max_datetime:
            params["max_datetime"] = max_datetime
        if location_id:
            params["location_id"] = location_id
        if full_raw is not None:
            params["full_raw"] = str(full_raw)

        page_size = max(1, min(int(page_limit), 10000))
        params["limit"] = str(page_size)
        params["offset"] = "0"

        path: str = "/alerts/history"
        request_params: Optional[Dict[str, str]] = params
        page_count = 0

        while True:
            page_count += 1
            data = self._request("GET", path, params=request_params)

            alerts: List[Dict[str, Any]] = []
            if isinstance(data, dict):
                alerts = data.get("alerts", [])
                if not alerts:
                    response = data.get("response") if isinstance(data.get("response"), dict) else None
                    if response:
                        alerts = response.get("alerts", [])

            for alert in alerts or []:
                yield alert

            next_page = data.get("next_page") if isinstance(data, dict) else None
            if not next_page:
                break

            if max_pages is not None and page_count >= max_pages:
                break

            path = next_page
            request_params = None

    def list_locations(self) -> dict:
        data = self._request("GET", "/locations")
        # Handle the actual API response structure: {"status": {...}, "response": {"locations": [...]}}
        response = data.get("response", {})
        locs = response.get("locations", [])
        # Return a dict id->description
        return {item.get("id"): item.get("description") for item in locs if isinstance(item, dict)}

    def create_project(
        self,
        name: str,
        tag_url: str,
        locations: dict,
        auto_scan: bool = True,
        scan_type: int = 1,
        times_per_day: int = 1,
        ext_lineitem_id: Optional[str] = None
    ) -> dict:
        """
        Create a new scan project/campaign with city-level targeting.
        
        Args:
            name: Project name
            tag_url: URL to scan/monitor
            locations: Dict of location_id -> description (e.g., {"Z0": "New York City, NY"})
            auto_scan: Enable automatic scanning (default: True)
            scan_type: Scan type ID - valid values are 1, 2, 5, 7, 8 (default: 1)
            times_per_day: How many times per day to scan (default: 1)
            ext_lineitem_id: External line item ID (optional)
        
        Returns:
            Project creation response dict
            
        Example:
            # Create NYC-targeted campaign
            project = client.create_project(
                name="NYC Campaign Test",
                tag_url="https://example.com",
                locations={"Z0": "New York City, NY"}
            )
            
            # Create multi-city campaign
            project = client.create_project(
                name="Multi-City Campaign",
                tag_url="https://example.com", 
                locations={"Z0": "New York City, NY", "Z2": "Chicago, IL"}
            )
        """
        import json
        
        # Prepare form data payload
        payload = {
            "name": name,
            "tag": tag_url,
            "auto_scan": "1" if auto_scan else "0",
            "scan_type": str(scan_type),
            "times_per_day": str(times_per_day)
        }
        
        # Add locations - try different formats based on API testing
        if len(locations) == 1:
            # Single location - use location_id format
            location_id = list(locations.keys())[0]
            payload["location_id"] = location_id
            payload["locations"] = location_id
        else:
            # Multiple locations - use comma-separated format
            location_ids = ",".join(locations.keys())
            payload["location_id"] = location_ids
            payload["locations"] = location_ids
        
        if ext_lineitem_id:
            payload["ext_lineitem_id"] = ext_lineitem_id
        
        # Create project using form data (not JSON)
        import requests
        url = f"{self.base_url}/projects"
        headers = {"Authorization": self.api_key}
        
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        
        try:
            result = response.json()
        except ValueError:
            response.raise_for_status()
            return {}
            
        if not response.ok and isinstance(result, dict) and "status" in result:
            msg = result["status"]
            raise requests.HTTPError(f"GeoEdge API error: {msg}", response=response)
            
        response.raise_for_status()
        return result

    # -------------------------------
    # Higher-level helpers
    # -------------------------------
    def fetch_projects_with_locations(
        self,
        *,
        page_limit: int = 1000,
        max_workers: int = 12,
    ) -> List[dict]:
        """Return detailed project dicts (includes locations) by fetching each project."""
        # 1) Collect minimal list first
        minimal = list(self.iter_projects_list(limit=page_limit))
        ids = [p["id"] for p in minimal if "id" in p]

        # 2) Fetch details concurrently
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results: List[dict] = []
        errors: List[Tuple[str, Exception]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            fut_to_id = {ex.submit(self.get_project, pid): pid for pid in ids}
            for fut in as_completed(fut_to_id):
                pid = fut_to_id[fut]
                try:
                    proj = fut.result()
                    if proj:
                        results.append(proj)
                except Exception as e:
                    errors.append((pid, e))
        # Optional: print or log errors
        if errors:
            # Keep silent by default; caller can choose to show debug
            pass
        return results

    def filter_projects_by_country_codes(
        self, projects: Iterable[dict], country_codes: Iterable[str]
    ) -> List[dict]:
        target = {c.strip().upper() for c in country_codes if c}
        out = []
        for p in projects:
            locs = p.get("locations") or {}
            loc_keys = {k.upper() for k in locs.keys()} if isinstance(locs, dict) else set()
            if target & loc_keys:
                out.append(p)
        return out
