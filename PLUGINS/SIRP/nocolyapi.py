from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict
from typing import List, Any

import requests
from requests.adapters import HTTPAdapter

from Lib.log import logger
from Lib.configs import get_local_data_path
from Lib.xcache import Xcache
try:
    from PLUGINS.SIRP.CONFIG import SIRP_URL, SIRP_APPKEY, SIRP_SIGN
except ModuleNotFoundError:
    from PLUGINS.SIRP.config_runtime import SIRP_URL, SIRP_APPKEY, SIRP_SIGN
from PLUGINS.SIRP.nocolymodel import FieldType, OptionType

# SESSION
HEADERS = {"HAP-Appkey": SIRP_APPKEY,
           "HAP-Sign": SIRP_SIGN}

SIRP_REQUEST_TIMEOUT = 10  # seconds

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)
HTTP_SESSION.verify = False
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10
)
HTTP_SESSION.mount('http://', adapter)
HTTP_SESSION.mount('https://', adapter)

SYSTEM_FIELDS = ['rowid', 'ownerid', 'caid', 'ctime', 'utime', 'uaid', 'wfname', 'wfcuaids', 'wfcaid', 'wfctime', 'wfrtime', 'wfcotime', 'wfdtime', 'wfftime',
                 'wfstatus']
LOCAL_SIRP_ENABLED = os.getenv("ASF_LOCAL_SIRP", "0") == "1"
LOCAL_SIRP_STORE_PATH = get_local_data_path("local_sirp_store.json")
_LOCAL_SIRP_LOCK = threading.Lock()


def _local_sirp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_local_sirp_dir():
    os.makedirs(os.path.dirname(LOCAL_SIRP_STORE_PATH), exist_ok=True)


def _load_local_sirp_store() -> Dict[str, Dict[str, dict]]:
    _ensure_local_sirp_dir()
    if not os.path.exists(LOCAL_SIRP_STORE_PATH):
        return {}
    try:
        with open(LOCAL_SIRP_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_local_sirp_store(store: Dict[str, Dict[str, dict]]) -> None:
    _ensure_local_sirp_dir()
    with open(LOCAL_SIRP_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _local_sirp_get_rows(worksheet_id: str) -> Dict[str, dict]:
    with _LOCAL_SIRP_LOCK:
        store = _load_local_sirp_store()
        return store.get(worksheet_id, {}).copy()


def _local_sirp_write_rows(worksheet_id: str, rows: Dict[str, dict]) -> None:
    with _LOCAL_SIRP_LOCK:
        store = _load_local_sirp_store()
        store[worksheet_id] = rows
        _save_local_sirp_store(store)


def _local_sirp_match_condition(row: dict, condition: dict) -> bool:
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")
    actual = row.get(field)

    if operator == "eq":
        return actual == expected
    if operator == "in":
        if isinstance(expected, list):
            return actual in expected
        return actual == expected
    if operator == "contains":
        if isinstance(actual, list):
            if isinstance(expected, list):
                return all(item in actual for item in expected)
            return expected in actual
        if isinstance(actual, str):
            if isinstance(expected, list):
                return all(str(item) in actual for item in expected)
            return str(expected) in actual
    if operator == "isnotempty":
        return actual not in (None, "", [], {})
    if operator == "isempty":
        return actual in (None, "", [], {})
    return True


def _local_sirp_match_filter(row: dict, filter_data: dict) -> bool:
    if not filter_data:
        return True

    filter_type = filter_data.get("type")
    if filter_type == "group":
        children = filter_data.get("children", [])
        logic = filter_data.get("logic", "AND")
        if logic == "OR":
            return any(_local_sirp_match_filter(row, child) for child in children)
        return all(_local_sirp_match_filter(row, child) for child in children)
    if filter_type == "condition":
        return _local_sirp_match_condition(row, filter_data)
    return True


def _local_sirp_fields_to_row(fields: List[Dict[str, Any]]) -> dict:
    row = {}
    for field in fields:
        row[field.get("id")] = field.get("value")
    return row


class Worksheet(object):
    def __init__(self):
        pass

    @staticmethod
    def get_fields(worksheet_id: str) -> Dict[str, FieldType]:
        if LOCAL_SIRP_ENABLED:
            return {}
        cached_fields = Xcache.get_sirp_fields(worksheet_id)
        if cached_fields is not None:
            return cached_fields

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}"

        response = HTTP_SESSION.get(
            url
        )
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            fields_list: List[FieldType] = response_data.get("data").get("fields")
            fields_dict = {}
            for field in fields_list:
                if field["id"] not in SYSTEM_FIELDS:
                    fields_dict[field["alias"]] = field
                else:
                    fields_dict[field["id"]] = field
            Xcache.set_sirp_fields(worksheet_id, fields_dict)
            return fields_dict
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")


class WorksheetRow(object):
    def __init__(self):
        pass

    @staticmethod
    def _format_input_row(row, fields, include_system_fields=True) -> dict:
        data_new = {}
        for alias in row:
            if alias in SYSTEM_FIELDS:
                if include_system_fields or alias == "rowid":
                    data_new[alias] = row[alias]
                else:
                    continue
            else:
                field = fields.get(alias)

                if field is None:
                    logger.warning(f"field {alias} not found in fields")
                    for key in fields:
                        if fields[key]['id'] == alias:
                            logger.warning(f"error field  is '{fields[key]['name']}'")
                            logger.warning(f"row data : {row}")

                    continue
                data_new[alias] = WorksheetRow._format_input_value(field, row[alias])
        return data_new

    @staticmethod
    def _format_input_value(field, value):
        field_type = field.get("type")
        sub_type = field.get("subType")
        if field_type in ["MultipleSelect"]:
            value_list = []
            for option in value:
                value_list.append(option.get("value"))
            return value_list
        elif field_type in ['SingleSelect', "Dropdown"]:
            if len(value) > 0:
                return value[0].get("value")
            else:
                return None
        elif field_type in ['Relation']:
            if sub_type == 1:
                value_list = []
                for option in value:
                    value_list.append(option.get("sid"))
                return value_list
            else:
                return value
        elif field_type in ['Checkbox']:
            return bool(int(value))
        else:
            return value

    @staticmethod
    def _format_output_value(fields_config, fields):
        fields_new = []
        for field in fields:
            field_key = field.get("id")
            field_config = fields_config.get(field_key)
            if field_config is None:
                raise Exception(f"field {field_key} not found in fields_config")

            field_type = field_config.get("type")
            sub_type = field_config.get("subType")
            value = field.get("value")

            if field_type in ['Checkbox']:
                field["value"] = 1 if value else 0
            if field_type in ['Collaborator']:
                if value:
                    if isinstance(value, list):
                        field["value"] = value[0].get('accountId')
                    else:
                        field["value"] = value.get('accountId')
            fields_new.append(field)
        return fields_new

    @staticmethod
    def _translate_filter_names_to_ids(filter_data, fields_config):
        if filter_data.get("type") == "group":
            for child in filter_data.get("children", []):
                WorksheetRow._translate_filter_names_to_ids(child, fields_config)

        elif filter_data.get("type") == "condition":
            if filter_data.get("operator") == "in" and isinstance(filter_data.get("value"), list):
                field_key = filter_data.get("field")

                target_field = fields_config.get(field_key)
                if not target_field:
                    for f in fields_config.values():
                        if f.get("id") == field_key:
                            target_field = f
                            break

                if target_field and target_field.get("options"):
                    value_to_key = {opt["value"]: opt["key"] for opt in target_field["options"]}
                    filter_data["value"] = [value_to_key.get(v, v) for v in filter_data["value"]]

    @staticmethod
    def get(worksheet_id: str, row_id: str, include_system_fields=True) -> dict:
        if LOCAL_SIRP_ENABLED:
            rows = _local_sirp_get_rows(worksheet_id)
            row = rows.get(row_id)
            if row is None:
                raise Exception(f"local_sirp row not found: {worksheet_id}/{row_id}")
            if include_system_fields:
                return row.copy()
            return {k: v for k, v in row.items() if k not in SYSTEM_FIELDS}
        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/{row_id}"
        fields = Worksheet.get_fields(worksheet_id)
        response = HTTP_SESSION.get(
            url,
            timeout=SIRP_REQUEST_TIMEOUT,
            params={"includeSystemFields": include_system_fields}
        )
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            row = response_data.get("data")
            data_new = WorksheetRow._format_input_row(row, fields, include_system_fields)
            return data_new
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def list(worksheet_id: str, filter: dict, fields=[], include_system_fields=True) -> List:
        if LOCAL_SIRP_ENABLED:
            rows = _local_sirp_get_rows(worksheet_id)
            result = []
            for row in rows.values():
                if _local_sirp_match_filter(row, filter):
                    row_data = row.copy() if include_system_fields else {k: v for k, v in row.items() if k not in SYSTEM_FIELDS}
                    if fields:
                        row_data = {k: v for k, v in row_data.items() if k in fields or k in SYSTEM_FIELDS}
                    result.append(row_data)
            result.sort(key=lambda item: item.get("utime", ""), reverse=True)
            return result
        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/list"
        all_rows = []
        page_index = 1
        page_size = 1000
        fields_config = Worksheet.get_fields(worksheet_id)
        WorksheetRow._translate_filter_names_to_ids(filter, fields_config)
        while True:
            data = {
                "filter": filter,
                "fields": fields,
                "sorts": [
                    {
                        "field": "utime",
                        "isAsc": False
                    }
                ],
                "includeTotalCount": True,
                "pageSize": page_size,
                "pageIndex": page_index
            }

            response = HTTP_SESSION.post(url,
                                         timeout=SIRP_REQUEST_TIMEOUT,
                                         headers=HEADERS,
                                         json=data)
            response.raise_for_status()
            response_data = response.json()

            if not response_data.get("success"):
                raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

            result_data = response_data.get("data")
            rows = result_data.get("rows")
            total_count = result_data.get("total", 0)

            if not rows:
                break

            for row in rows:
                formatted_row = WorksheetRow._format_input_row(row, fields_config, include_system_fields)
                all_rows.append(formatted_row)

            if len(all_rows) >= total_count:
                break

            page_index += 1

        return all_rows

    @staticmethod
    def create(worksheet_id: str, fields: List, trigger_workflow: bool = True):
        if LOCAL_SIRP_ENABLED:
            with _LOCAL_SIRP_LOCK:
                store = _load_local_sirp_store()
                rows = store.get(worksheet_id, {})
                rowid = str(uuid.uuid4())
                now = _local_sirp_now()
                row = _local_sirp_fields_to_row(fields)
                row["rowid"] = rowid
                row.setdefault("ctime", now)
                row["utime"] = now
                rows[rowid] = row
                store[worksheet_id] = rows
                _save_local_sirp_store(store)
            logger.info(f"[local_sirp] created {worksheet_id} row {rowid}")
            return rowid

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows"
        fields_config = Worksheet.get_fields(worksheet_id)
        fields = WorksheetRow._format_output_value(fields_config, fields)
        data = {
            "triggerWorkflow": trigger_workflow,
            "fields": fields
        }

        try:
            response = HTTP_SESSION.post(url,
                                         timeout=SIRP_REQUEST_TIMEOUT,
                                         json=data)
            response.raise_for_status()

            response_data = response.json()
            if response_data.get("success"):
                return response_data.get("data").get("id")
            else:
                raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')} data: {response_data.get('data')}")
        except Exception as e:
            raise e

    @staticmethod
    def update(worksheet_id: str, row_id: str, fields: List, trigger_workflow: bool = True):
        if LOCAL_SIRP_ENABLED:
            with _LOCAL_SIRP_LOCK:
                store = _load_local_sirp_store()
                rows = store.get(worksheet_id, {})
                if row_id not in rows:
                    raise Exception(f"local_sirp row not found for update: {worksheet_id}/{row_id}")
                row = rows[row_id]
                row.update(_local_sirp_fields_to_row(fields))
                row["utime"] = _local_sirp_now()
                rows[row_id] = row
                store[worksheet_id] = rows
                _save_local_sirp_store(store)
            logger.info(f"[local_sirp] updated {worksheet_id} row {row_id}")
            return row_id

        fields_config = Worksheet.get_fields(worksheet_id)
        fields = WorksheetRow._format_output_value(fields_config, fields)
        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/{row_id}"

        data = {
            "triggerWorkflow": trigger_workflow,
            "fields": fields
        }
        response = HTTP_SESSION.patch(url,
                                      timeout=SIRP_REQUEST_TIMEOUT,
                                      json=data)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            return response_data.get("data")
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def batch_create(worksheet_id: str,
                     rows: List[List[Dict]],
                     trigger_workflow: bool = True) -> Dict:
        if LOCAL_SIRP_ENABLED:
            row_ids = []
            for row_fields in rows:
                row_ids.append(WorksheetRow.create(worksheet_id, row_fields, trigger_workflow=trigger_workflow))
            return {"rowIds": row_ids}

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/batch"
        fields_config = Worksheet.get_fields(worksheet_id)

        formatted_rows = []
        for row_fields in rows:
            formatted_fields = WorksheetRow._format_output_value(fields_config, row_fields)
            formatted_rows.append({"fields": formatted_fields})

        data = {
            "rows": formatted_rows,
            "triggerWorkflow": trigger_workflow
        }

        try:
            response = HTTP_SESSION.post(url,
                                         timeout=SIRP_REQUEST_TIMEOUT,
                                         json=data)
            response.raise_for_status()

            response_data = response.json()
            if response_data.get("success"):
                return response_data.get("data")  # {"rowIds":[rowid1,rowid2]}
            else:
                raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')} data: {response_data.get('data')}")
        except Exception as e:
            raise e

    @staticmethod
    def batch_update(worksheet_id: str,
                     rowids: List[str],
                     fields: List[Dict],
                     trigger_workflow: bool = True) -> Dict:
        if LOCAL_SIRP_ENABLED:
            success = []
            failed = []
            for rowid in rowids:
                try:
                    WorksheetRow.update(worksheet_id, rowid, fields, trigger_workflow=trigger_workflow)
                    success.append(rowid)
                except Exception:
                    failed.append(rowid)
            return {"failedRowIds": failed, "successfulRowIds": success}

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/batch"
        fields_config = Worksheet.get_fields(worksheet_id)

        fields = WorksheetRow._format_output_value(fields_config, fields)

        data = {
            "rowIds": rowids,
            "fields": fields,
            "triggerWorkflow": trigger_workflow
        }

        try:
            response = HTTP_SESSION.patch(url,
                                          timeout=SIRP_REQUEST_TIMEOUT,
                                          json=data)
            response.raise_for_status()

            response_data = response.json()
            if response_data.get("success"):
                return response_data.get("data")  # {"failedRowIds":[rowid1,rowid2], "successfulRowIds":[rowid3,rowid4]}
            else:
                raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')} data: {response_data.get('data')}")
        except Exception as e:
            raise e

    @staticmethod
    def delete(worksheet_id: str, rowid: List, trigger_workflow: bool = True):
        if LOCAL_SIRP_ENABLED:
            with _LOCAL_SIRP_LOCK:
                store = _load_local_sirp_store()
                rows = store.get(worksheet_id, {})
                deleted = rows.pop(rowid, None)
                store[worksheet_id] = rows
                _save_local_sirp_store(store)
            return deleted is not None
        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/{rowid}"

        data = {
            "triggerWorkflow": trigger_workflow,
        }

        response = HTTP_SESSION.delete(url,
                                       timeout=SIRP_REQUEST_TIMEOUT,
                                       json=data)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            return response_data.get("data")
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def batch_delete(worksheet_id: str, row_ids: List, trigger_workflow: bool = True):
        if LOCAL_SIRP_ENABLED:
            with _LOCAL_SIRP_LOCK:
                store = _load_local_sirp_store()
                rows = store.get(worksheet_id, {})
                for rowid in row_ids:
                    rows.pop(rowid, None)
                store[worksheet_id] = rows
                _save_local_sirp_store(store)
            return {"rowids": row_ids}

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/batch"

        data = {
            "rowids": row_ids,
            "triggerWorkflow": trigger_workflow,
        }

        response = HTTP_SESSION.delete(url,
                                       timeout=SIRP_REQUEST_TIMEOUT,
                                       json=data)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            return response_data.get("data")
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def get_discussions(worksheet_id: str, row_id: str) -> List[Dict]:
        if LOCAL_SIRP_ENABLED:
            return []
        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/{row_id}/discussions"

        response = HTTP_SESSION.get(url,
                                    timeout=SIRP_REQUEST_TIMEOUT)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            # [
            #     {
            #         "id": "讨论ID",
            #         "message": "讨论内容",
            #         "_createdAt": "创建时间",
            #         "_createdBy": {"id", "name", "avatar", "isPortal", "status"},
            #         "replyToAuthor": {"id", "name", "avatar", "isPortal", "status"},
            #         "replyId": "回复ID",
            #         "projectId": "项目ID",
            #         "replyToId": [],
            #         "mentions": [],
            #         "attachments": [
            #             {"originalFilename", "ext", "filesize", "downloadUrl"}
            #         ]
            #     }
            # ]
            discussions = response_data.get("data", {}).get("discussions", [])
            return discussions
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def relations(worksheet_id: str, row_id: str, field: str, relation_worksheet_id: str, include_system_fields: bool = True, page_size: int = 1000,
                  page_index: int = 1):
        if LOCAL_SIRP_ENABLED:
            row = WorksheetRow.get(worksheet_id, row_id, include_system_fields=True)
            relation_ids = row.get(field, []) or []
            if not isinstance(relation_ids, list):
                relation_ids = [relation_ids]
            related_rows = []
            for relation_id in relation_ids:
                try:
                    related_rows.append(WorksheetRow.get(relation_worksheet_id, relation_id, include_system_fields=include_system_fields))
                except Exception:
                    continue
            return related_rows
        fields = Worksheet.get_fields(relation_worksheet_id)

        url = f"{SIRP_URL}/api/v3/app/worksheets/{worksheet_id}/rows/{row_id}/relations/{field}"

        params = {}
        if page_size is not None:
            params["pageSize"] = page_size
        if page_index is not None:
            params["pageIndex"] = page_index
        if include_system_fields is not None:
            params["isReturnSystemFields"] = include_system_fields

        response = HTTP_SESSION.get(url,
                                    timeout=SIRP_REQUEST_TIMEOUT,
                                    params=params)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            rows = response_data.get("data").get("rows")
            rows_new = []
            for row in rows:
                data_new = WorksheetRow._format_input_row(row, fields, include_system_fields)
                rows_new.append(data_new)
            return rows_new
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def get_rowid_list_from_rowid(rowid):
        # 多行数据获取列表
        tmp = rowid.split("_")
        rowid_list = tmp[0].split(",")
        return rowid_list


class OptionSet(object):
    def __init__(self):
        pass

    @staticmethod
    def list():
        if LOCAL_SIRP_ENABLED:
            return []
        cached_optionsets = Xcache.get_sirp_optionset()
        if cached_optionsets is not None:
            return cached_optionsets
        url = f"{SIRP_URL}/api/v3/app/optionsets"

        response = HTTP_SESSION.get(url,
                                    timeout=SIRP_REQUEST_TIMEOUT)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("success"):
            optionsets: List[Dict[str, Any]] = response_data.get("data").get("optionsets")
            Xcache.set_sirp_optionset(optionsets)
            return optionsets
        else:
            raise Exception(f"error_code: {response_data.get('error_code')} error_msg: {response_data.get('error_msg')}")

    @staticmethod
    def get(name):
        optionsets = OptionSet.list()
        for optionset in optionsets:
            if optionset["name"] == name:
                options = optionset.get("options", [])
                return options
        raise Exception(f"optionset {name} not found")

    @staticmethod
    def get_option_by_name_and_value(name, value) -> OptionType:
        optionsets = OptionSet.list()
        for optionset in optionsets:
            if optionset["name"] == name:
                options = optionset.get("options", [])
                for option in options:
                    if option["value"] == value:
                        return option
        raise Exception(f"optionset {name} {value} not found")

    @staticmethod
    def get_option_key_by_name_and_value(name, value):
        optionsets = OptionSet.list()
        for optionset in optionsets:
            if optionset["name"] == name:
                options = optionset.get("options", [])
                for option in options:
                    if option["value"] == value:
                        return option["key"]
        raise Exception(f"optionset {name} {value} not found")


if __name__ == "__main__":
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ASP.settings")
    import django

    django.setup()
    result = WorksheetRow.get_discussions("case", "55c0ac33-65c2-420d-8e90-3ac62ca46f85")
    print(result)
