"""
Hikvision ISAPI client tailored for the DS-K1T32x / DS-K1T34x series
MinMoe face-recognition terminals (currently deployed: DS-K1T323MBFWX-E1
with Wi-Fi, fingerprint, IP65, deep-learning recognition).

The same ISAPI endpoints are used regardless of whether the device is
reached over Wi-Fi or Ethernet — both deliver the device on the same
campus IP network as the server.

Design rationale
----------------
The DS-K1T323MBFWX-E1 exposes its full feature set through ISAPI (Hikvision's
HTTP-based Intelligent Security API), authenticated with HTTP Digest. The
relevant ISAPI endpoints we use for the UPSA attendance use case are:

    GET  /ISAPI/System/deviceInfo                -> device identity
    POST /ISAPI/AccessControl/UserInfo/Record    -> add a person (employee)
    PUT  /ISAPI/AccessControl/UserInfo/Modify    -> update a person
    POST /ISAPI/AccessControl/UserInfo/Delete    -> delete a person
    POST /ISAPI/Intelligent/FDLib/FaceDataRecord -> add a face picture for a person
    POST /ISAPI/AccessControl/AcsEvent           -> search recognition events
    PUT  /ISAPI/Event/notification/httpHosts     -> register our event listener
    GET  /ISAPI/AccessControl/UserInfo/Search    -> list enrolled persons

We deliberately keep this module dependency-light: only `requests` and the
standard library, so it runs on a vanilla Python 3.10+ environment.

Notes on real-vs-simulated mode
-------------------------------
Out of the box, with no terminal on the LAN, the client will fail-fast with a
clear ConnectionError. For development and panel-defence rehearsal, the client
also exposes a `simulate=True` flag that returns canned responses, so the rest
of the application can be exercised end-to-end without the device on the desk.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests.auth import HTTPDigestAuth
import xmltodict

log = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    device_name: str
    device_id: str
    model: str
    serial_no: str
    firmware_version: str
    mac_address: str


class HikvisionTerminal:
    """Thin, well-typed wrapper around the ISAPI endpoints we actually need."""

    def __init__(
        self,
        host: str,
        port: int = 80,
        username: str = "admin",
        password: str = "",
        timeout: int = 10,
        simulate: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.simulate = simulate
        self.base_url = f"http://{host}:{port}"
        self.auth = HTTPDigestAuth(username, password)

    # ------------------------------------------------------------------ helpers
    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        xml_body: str | None = None,
        params: dict | None = None,
        files: dict | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {}
        data = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body)
        elif xml_body is not None:
            headers["Content-Type"] = "application/xml"
            data = xml_body
        log.debug("Hik %s %s", method, url)
        return requests.request(
            method,
            url,
            auth=self.auth,
            headers=headers,
            data=data,
            params=params,
            files=files,
            timeout=self.timeout,
        )

    @staticmethod
    def _parse(resp: requests.Response) -> dict:
        ctype = resp.headers.get("Content-Type", "")
        try:
            if "json" in ctype:
                return resp.json()
            return xmltodict.parse(resp.text)
        except Exception:  # pragma: no cover
            return {"raw": resp.text}

    # ------------------------------------------------------------------ device
    def get_device_info(self) -> Optional[dict]:
        if self.simulate:
            return {
                "deviceName": "DS-K1T323MBFWX-E1 (simulated)",
                "deviceID": "SIM-0001",
                "model": "DS-K1T323MBFWX-E1",
                "serialNumber": "GM6647437",
                "firmwareVersion": "V4.3.0 build 240301",
                "macAddress": "AA:BB:CC:DD:EE:FF",
            }
        try:
            r = self._request("GET", "/ISAPI/System/deviceInfo")
            if r.status_code != 200:
                return None
            data = self._parse(r)
            di = data.get("DeviceInfo", data)
            return {
                "deviceName": di.get("deviceName"),
                "deviceID": di.get("deviceID"),
                "model": di.get("model"),
                "serialNumber": di.get("serialNumber"),
                "firmwareVersion": di.get("firmwareVersion"),
                "macAddress": di.get("macAddress"),
            }
        except requests.RequestException as e:
            log.warning("Hikvision unreachable: %s", e)
            return None

    # ------------------------------------------------------------------ persons
    def add_person(
        self,
        employee_id: str,
        name: str,
        gender: str = "male",
        valid_begin: str = "2020-01-01T00:00:00",
        valid_end: str = "2030-12-31T23:59:59",
    ) -> tuple[bool, str]:
        """
        Adds a person record. The terminal stores up to 50,000 user entries
        (and 1,500 face pictures) per the manual.
        """
        if self.simulate:
            return True, f"[simulated] added {employee_id}"

        body = {
            "UserInfo": {
                "employeeNo": str(employee_id),
                "name": name,
                "userType": "normal",
                "gender": gender,
                "Valid": {
                    "enable": True,
                    "beginTime": valid_begin,
                    "endTime": valid_end,
                    "timeType": "local",
                },
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
            }
        }
        try:
            r = self._request(
                "POST",
                "/ISAPI/AccessControl/UserInfo/Record?format=json",
                json_body=body,
            )
            ok = r.status_code in (200, 201)
            return ok, r.text
        except requests.RequestException as e:
            return False, str(e)

    def delete_person(self, employee_id: str) -> tuple[bool, str]:
        if self.simulate:
            return True, f"[simulated] deleted {employee_id}"
        body = {
            "UserInfoDelCond": {
                "EmployeeNoList": [{"employeeNo": str(employee_id)}]
            }
        }
        try:
            r = self._request(
                "PUT",
                "/ISAPI/AccessControl/UserInfo/Delete?format=json",
                json_body=body,
            )
            return r.status_code == 200, r.text
        except requests.RequestException as e:
            return False, str(e)

    def list_persons(self, search_id: str = "1", max_results: int = 30) -> dict:
        if self.simulate:
            return {"UserInfoSearch": {"UserInfo": [], "totalMatches": 0}}
        body = {
            "UserInfoSearchCond": {
                "searchID": search_id,
                "searchResultPosition": 0,
                "maxResults": max_results,
            }
        }
        try:
            r = self._request(
                "POST",
                "/ISAPI/AccessControl/UserInfo/Search?format=json",
                json_body=body,
            )
            return self._parse(r)
        except requests.RequestException as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ faces
    def add_face_picture(
        self,
        employee_id: str,
        image_bytes: bytes,
    ) -> tuple[bool, str]:
        """
        Uploads a face picture for an existing person.

        ISAPI requires multipart/form-data with two parts:
            FaceDataRecord  (JSON metadata)
            FaceImage       (the JPG/PNG itself)
        """
        if self.simulate:
            return True, f"[simulated] face uploaded for {employee_id}"
        meta = {
            "faceLibType": "blackFD",
            "FDID": "1",
            "FPID": str(employee_id),
        }
        try:
            files = {
                "FaceDataRecord": (
                    None,
                    json.dumps(meta),
                    "application/json",
                ),
                "img": (
                    f"{employee_id}.jpg",
                    image_bytes,
                    "image/jpeg",
                ),
            }
            r = self._request(
                "POST",
                "/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json",
                files=files,
            )
            return r.status_code in (200, 201), r.text
        except requests.RequestException as e:
            return False, str(e)

    # ------------------------------------------------------------------ events
    def search_events(
        self,
        start_iso: str,
        end_iso: str,
        max_results: int = 100,
    ) -> list[dict]:
        """
        Pulls recognition events from the device for a given time window.
        Returned each event has at minimum: time, employeeNoString, similarity,
        and may include a snapshot picture URL.
        """
        if self.simulate:
            return []
        body = {
            "AcsEventCond": {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": max_results,
                "major": 5,  # 5 == access controller events
                "minor": 75,  # 75 == authentication via face
                "startTime": start_iso,
                "endTime": end_iso,
            }
        }
        try:
            r = self._request(
                "POST",
                "/ISAPI/AccessControl/AcsEvent?format=json",
                json_body=body,
            )
            data = self._parse(r)
            return (
                data.get("AcsEvent", {}).get("InfoList", [])
                if isinstance(data, dict)
                else []
            )
        except requests.RequestException as e:
            log.warning("search_events failed: %s", e)
            return []

    # ----------------------------------------------------- listener registration
    def register_event_listener(
        self,
        listener_url: str,
        listener_id: int = 1,
        protocol: str = "HTTP",
        format_: str = "JSON",
    ) -> tuple[bool, str]:
        """
        Tells the terminal: "POST every recognition event to {listener_url}".

        After this call, our Flask /api/v1/events/hik endpoint receives every
        face match in real time, with no polling required.
        """
        if self.simulate:
            return True, f"[simulated] listener registered at {listener_url}"
        body = {
            "HttpHostNotification": {
                "id": str(listener_id),
                "url": listener_url,
                "protocolType": protocol,
                "parameterFormatType": format_,
                "addressingFormatType": "ipaddress",
                "ipAddress": listener_url.split("://")[-1].split(":")[0],
                "portNo": int(listener_url.split(":")[-1].split("/")[0])
                if ":" in listener_url.split("://")[-1]
                else 80,
                "httpAuthenticationMethod": "none",
            }
        }
        try:
            r = self._request(
                "PUT",
                f"/ISAPI/Event/notification/httpHosts/{listener_id}?format=json",
                json_body=body,
            )
            return r.status_code == 200, r.text
        except requests.RequestException as e:
            return False, str(e)
