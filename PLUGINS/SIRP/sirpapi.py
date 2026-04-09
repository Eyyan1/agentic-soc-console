import json
import os
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import List, Union, Annotated

import requests

from Core.localdev_playbooks import select_local_case_playbook_name
from Lib.log import logger
try:
    from PLUGINS.SIRP.CONFIG import SIRP_NOTICE_WEBHOOK
except ModuleNotFoundError:
    from PLUGINS.SIRP.config_runtime import SIRP_NOTICE_WEBHOOK
from PLUGINS.SIRP.nocolyapi import WorksheetRow
from PLUGINS.SIRP.nocolymodel import AccountModel, Condition, Group, Operator
from PLUGINS.SIRP.sirpbase import BaseWorksheetEntity
from PLUGINS.SIRP.sirpmodel import EnrichmentModel, ArtifactModel, AlertModel, CaseModel, TicketModel, MessageModel, PlaybookModel, PlaybookJobStatus, \
    KnowledgeAction, KnowledgeModel, Severity, Confidence, PlaybookType, CaseStatus


LOCAL_SIRP_ENABLED = os.getenv("ASF_LOCAL_SIRP", "0") == "1"
SIRP_KNOWLEDGE_COLLECTION = "SIRP_KNOWLEDGE_COLLECTION"


def _get_embeddings_search_client():
    if os.getenv("ASF_DISABLE_EMBEDDINGS", "0") == "1":
        return None, SIRP_KNOWLEDGE_COLLECTION
    try:
        from PLUGINS.Embeddings.embeddings_qdrant import (
            SIRP_KNOWLEDGE_COLLECTION as collection_name,
            embedding_api_singleton_qdrant,
        )
        return embedding_api_singleton_qdrant, collection_name
    except Exception:
        logger.exception("Embeddings client is unavailable; returning empty knowledge search results.")
        return None, SIRP_KNOWLEDGE_COLLECTION

def _is_local_phishing_alert(alert_model: AlertModel) -> bool:
    labels = set(alert_model.labels or [])
    return (
        alert_model.rule_id == "ES-Rule-21-Phishing-User-Report-Mail"
        or "phishing" in labels
        or "confirmed-phishing" in labels
    )


def _get_local_case_correlation_uid(alert_model: AlertModel, rowid: str) -> str:
    return alert_model.correlation_uid or alert_model.uid or alert_model.source_uid or rowid


def _extract_email_address(value: str) -> str:
    _, email_address = parseaddr(value or "")
    normalized = (email_address or value or "").strip().lower()
    return normalized


def _extract_email_domain(value: str) -> str:
    email_address = _extract_email_address(value)
    if "@" in email_address:
        return email_address.split("@", 1)[1]
    return ""


def _format_local_time_bucket(value) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            return value[:10]
    return "unknown-date"


def _build_local_phishing_correlation_uid(alert_model: AlertModel, rowid: str) -> str:
    try:
        raw_data = json.loads(alert_model.raw_data or "{}")
    except json.JSONDecodeError:
        raw_data = {}

    headers = raw_data.get("headers", {})
    target_email = _extract_email_address(headers.get("To", "")) or "unknown-target"
    sender_domain = _extract_email_domain(headers.get("From", "")) or "unknown-domain"
    time_bucket = _format_local_time_bucket(alert_model.first_seen_time)

    # Local correlation intentionally favors fewer cases for bundled mock data.
    # Group by alert type + target recipient + UTC day window. Sender domain is only
    # used as a deterministic fallback when the target recipient is unavailable.
    target_key = target_email if target_email != "unknown-target" else sender_domain
    return f"local-phishing|{alert_model.rule_id}|{target_key}|{time_bucket}"


class Enrichment(BaseWorksheetEntity[EnrichmentModel]):
    """Enrichment 实体类"""
    WORKSHEET_ID = "enrichment"
    MODEL_CLASS = EnrichmentModel


class Ticket(BaseWorksheetEntity[TicketModel]):
    """Ticket 实体类"""
    WORKSHEET_ID = "ticket"
    MODEL_CLASS = TicketModel

    @classmethod
    def get_by_id(cls, ticket_id, lazy_load=False) -> Union[TicketModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=ticket_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def update_by_id(
            cls,
            ticket_id: str,
            uid: Union[str, None] = None,
            title: Union[str, None] = None,
            status=None,
            type=None,
            src_url: Union[str, None] = None
    ) -> Union[str, None]:
        ticket_old = cls.get_by_id(ticket_id, lazy_load=True)
        if not ticket_old:
            return None

        ticket_new = TicketModel()
        ticket_new.rowid = ticket_old.rowid
        if uid is not None:
            ticket_new.uid = uid
        if title is not None:
            ticket_new.title = title
        if status is not None:
            ticket_new.status = status
        if type is not None:
            ticket_new.type = type
        if src_url is not None:
            ticket_new.src_url = src_url

        return cls.update(ticket_new)


class Artifact(BaseWorksheetEntity[ArtifactModel]):
    """Artifact 实体类 - 关联 Enrichment"""
    WORKSHEET_ID = "artifact"
    MODEL_CLASS = ArtifactModel

    @classmethod
    def _load_relations(cls, model: ArtifactModel, include_system_fields: bool = True) -> ArtifactModel:
        """加载关联的enrichments"""
        model.enrichments = Enrichment.list_by_rowids(
            model.enrichments,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        return model

    @classmethod
    def _prepare_for_save(cls, model: ArtifactModel) -> ArtifactModel:
        """保存前处理关联数据"""
        if model.enrichments is not None:
            model.enrichments = Enrichment.batch_update_or_create(model.enrichments)
        return model

    @classmethod
    def get_by_id(cls, artifact_id, lazy_load=False) -> Union[ArtifactModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=artifact_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def attach_enrichment(
            cls,
            artifact_id: str,
            enrichment_rowid: str
    ) -> Union[str, None]:
        artifact_old = cls.get_by_id(artifact_id, lazy_load=True)
        if not artifact_old:
            return None

        existing_enrichments = []
        for enrichment in artifact_old.enrichments or []:
            if isinstance(enrichment, str):
                existing_enrichments.append(enrichment)
            elif enrichment.rowid:
                existing_enrichments.append(enrichment.rowid)

        if enrichment_rowid in existing_enrichments:
            return enrichment_rowid

        artifact_new = ArtifactModel()
        artifact_new.rowid = artifact_old.rowid
        artifact_new.enrichments = [*existing_enrichments, enrichment_rowid]
        cls.update(artifact_new)

        return enrichment_rowid


class Alert(BaseWorksheetEntity[AlertModel]):
    """Alert 实体类 - 关联 Artifact 和 Enrichment"""
    WORKSHEET_ID = "alert"
    MODEL_CLASS = AlertModel

    @classmethod
    def _load_relations(cls, model: AlertModel, include_system_fields: bool = True) -> AlertModel:
        """加载关联的artifacts和enrichments"""
        model.artifacts = Artifact.list_by_rowids(
            model.artifacts,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        model.enrichments = Enrichment.list_by_rowids(
            model.enrichments,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        return model

    @classmethod
    def _prepare_for_save(cls, model: AlertModel) -> AlertModel:
        """保存前处理关联数据"""
        if model.artifacts is not None:
            model.artifacts = Artifact.batch_update_or_create(model.artifacts)

        if model.enrichments is not None:
            model.enrichments = Enrichment.batch_update_or_create(model.enrichments)

        return model

    @classmethod
    def create(cls, model: AlertModel) -> str:
        if LOCAL_SIRP_ENABLED and _is_local_phishing_alert(model):
            model.correlation_uid = _build_local_phishing_correlation_uid(model, model.rowid or "")

        rowid = super().create(model)

        if LOCAL_SIRP_ENABLED:
            try:
                cls._handle_local_dev_case_flow(rowid)
            except Exception as exc:
                logger.exception(exc)
                logger.warning(f"Local SOC auto-flow skipped for alert {rowid}: {exc}")

        return rowid

    @classmethod
    def _handle_local_dev_case_flow(cls, rowid: str) -> None:
        alert_model = cls.get(rowid, lazy_load=True)
        if not _is_local_phishing_alert(alert_model):
            return

        correlation_uid = _get_local_case_correlation_uid(alert_model, rowid)
        if _is_local_phishing_alert(alert_model):
            correlation_uid = _build_local_phishing_correlation_uid(alert_model, rowid)
        if alert_model.correlation_uid != correlation_uid:
            cls.update(AlertModel(rowid=rowid, correlation_uid=correlation_uid))
            alert_model.correlation_uid = correlation_uid

        existing_cases = Case.list_by_correlation_uid(correlation_uid, lazy_load=True)
        if existing_cases:
            case_model = existing_cases[0]
            linked_alerts = list(case_model.alerts or [])
            if rowid not in linked_alerts:
                Case.update(CaseModel(rowid=case_model.rowid, alerts=[*linked_alerts, rowid]))
                logger.info(f"[local_soc] linked alert {rowid} to case {case_model.rowid}")
            return

        case_model = CaseModel(
            title=f"Local SOC Case: {alert_model.title}",
            severity=alert_model.severity,
            confidence=alert_model.confidence,
            status=CaseStatus.NEW,
            category=alert_model.product_category,
            description=f"Auto-created local case for phishing alert {rowid}.",
            correlation_uid=correlation_uid,
            alerts=[rowid],
            tags=["local-dev", "auto-case", "phishing"],
        )
        case_rowid = Case.create(case_model)
        logger.info(f"[local_soc] auto-created case {case_rowid} for alert {rowid}")

        playbook = Playbook.add_pending_playbook(
            type=PlaybookType.CASE,
            name=select_local_case_playbook_name(
                rule_id=alert_model.rule_id,
                title=alert_model.title,
                product_category=alert_model.product_category,
            ),
            source_rowid=case_rowid,
            user_input="Auto-queued by local SOC pipeline",
        )
        logger.info(f"[local_soc] auto-queued playbook {playbook.rowid} for case {case_rowid}")

    @classmethod
    def get_by_id(cls, alert_id, lazy_load=False) -> Union[AlertModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=alert_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def update_by_id(
            cls,
            alert_id: str,
            severity_ai: Union[Severity, None] = None,
            confidence_ai: Union[Confidence, None] = None,
            comment_ai: Union[str, None] = None
    ) -> Union[str, None]:
        alert_old = cls.get_by_id(alert_id, lazy_load=True)
        if not alert_old:
            return None

        alert_new = AlertModel()
        alert_new.rowid = alert_old.rowid
        if severity_ai is not None:
            alert_new.severity_ai = severity_ai
        if confidence_ai is not None:
            alert_new.confidence_ai = confidence_ai
        if comment_ai is not None:
            alert_new.comment_ai = comment_ai

        return cls.update(alert_new)

    @classmethod
    def get_discussions(cls, alert_id) -> Union[List[dict], None]:
        alert_model = cls.get_by_id(alert_id, lazy_load=True)
        if not alert_model:
            return None
        return WorksheetRow.get_discussions(cls.WORKSHEET_ID, alert_model.rowid)

    @classmethod
    def attach_artifact(
            cls,
            alert_id: str,
            artifact_rowid: str
    ) -> Union[str, None]:
        alert_old = cls.get_by_id(alert_id, lazy_load=True)
        if not alert_old:
            return None

        existing_artifacts = []
        for artifact in alert_old.artifacts or []:
            if isinstance(artifact, str):
                existing_artifacts.append(artifact)
            elif artifact.rowid:
                existing_artifacts.append(artifact.rowid)

        if artifact_rowid in existing_artifacts:
            return artifact_rowid

        alert_new = AlertModel()
        alert_new.rowid = alert_old.rowid
        alert_new.artifacts = [*existing_artifacts, artifact_rowid]
        cls.update(alert_new)

        return artifact_rowid

    @classmethod
    def attach_enrichment(
            cls,
            alert_id: str,
            enrichment_rowid: str
    ) -> Union[str, None]:
        alert_old = cls.get_by_id(alert_id, lazy_load=True)
        if not alert_old:
            return None

        existing_enrichments = []
        for enrichment in alert_old.enrichments or []:
            if isinstance(enrichment, str):
                existing_enrichments.append(enrichment)
            elif enrichment.rowid:
                existing_enrichments.append(enrichment.rowid)

        if enrichment_rowid in existing_enrichments:
            return enrichment_rowid

        alert_new = AlertModel()
        alert_new.rowid = alert_old.rowid
        alert_new.enrichments = [*existing_enrichments, enrichment_rowid]
        cls.update(alert_new)

        return enrichment_rowid


class Case(BaseWorksheetEntity[CaseModel]):
    """Case 实体类 - 关联 Alert、Enrichment 和 Ticket"""
    WORKSHEET_ID = "case"
    MODEL_CLASS = CaseModel

    @classmethod
    def _load_relations(cls, model: CaseModel, include_system_fields: bool = True) -> CaseModel:
        """加载所有关联数据"""
        model.alerts = Alert.list_by_rowids(
            model.alerts,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        model.enrichments = Enrichment.list_by_rowids(
            model.enrichments,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        model.tickets = Ticket.list_by_rowids(
            model.tickets,
            include_system_fields=include_system_fields,
            lazy_load=False
        )
        return model

    @classmethod
    def _prepare_for_save(cls, model: CaseModel) -> CaseModel:
        """保存前处理关联数据"""
        if model.alerts is not None:
            model.alerts = Alert.batch_update_or_create(model.alerts)

        if model.enrichments is not None:
            model.enrichments = Enrichment.batch_update_or_create(model.enrichments)

        if model.tickets is not None:
            model.tickets = Ticket.batch_update_or_create(model.tickets)
        return model

    @classmethod
    def list_by_correlation_uid(cls, correlation_uid, lazy_load=False) -> List[CaseModel]:
        """根据correlation_uid查询关联的Case"""
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="correlation_uid",
                    operator=Operator.EQ,
                    value=correlation_uid
                )
            ]
        )
        return cls.list(filter_model, lazy_load=lazy_load)

    @classmethod
    def get_by_id(cls, case_id, lazy_load=False) -> Union[CaseModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=case_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def update_by_id(
            cls,
            case_id: str,
            severity: Union[Severity, None] = None,
            status=None,
            verdict=None,
            severity_ai: Union[Severity, None] = None,
            confidence_ai: Union[Confidence, None] = None,
            attack_stage_ai=None,
            comment_ai: Union[str, None] = None,
            verdict_ai=None,
            summary_ai: Union[str, None] = None
    ) -> Union[str, None]:
        case_old = cls.get_by_id(case_id, lazy_load=True)
        if not case_old:
            return None

        case_new = CaseModel()
        case_new.rowid = case_old.rowid
        if severity is not None:
            case_new.severity = severity
        if status is not None:
            case_new.status = status
        if verdict is not None:
            case_new.verdict = verdict
        if severity_ai is not None:
            case_new.severity_ai = severity_ai
        if confidence_ai is not None:
            case_new.confidence_ai = confidence_ai
        if attack_stage_ai is not None:
            case_new.attack_stage_ai = attack_stage_ai
        if comment_ai is not None:
            case_new.comment_ai = comment_ai
        if verdict_ai is not None:
            case_new.verdict_ai = verdict_ai
        if summary_ai is not None:
            case_new.summary_ai = summary_ai

        return cls.update(case_new)

    @classmethod
    def get_discussions(cls, case_id) -> Union[List[dict], None]:
        case_model = cls.get_by_id(case_id, lazy_load=True)
        if not case_model:
            return None
        return WorksheetRow.get_discussions(cls.WORKSHEET_ID, case_model.rowid)

    @classmethod
    def attach_enrichment(
            cls,
            case_id: str,
            enrichment_rowid: str
    ) -> Union[str, None]:
        case_old = cls.get_by_id(case_id, lazy_load=True)
        if not case_old:
            return None

        existing_enrichments = []
        for enrichment in case_old.enrichments or []:
            if isinstance(enrichment, str):
                existing_enrichments.append(enrichment)
            elif enrichment.rowid:
                existing_enrichments.append(enrichment.rowid)

        if enrichment_rowid in existing_enrichments:
            return enrichment_rowid

        case_new = CaseModel()
        case_new.rowid = case_old.rowid
        case_new.enrichments = [*existing_enrichments, enrichment_rowid]
        cls.update(case_new)

        return enrichment_rowid

    @classmethod
    def attach_ticket(
            cls,
            case_id: str,
            ticket_rowid: str
    ) -> Union[str, None]:
        case_old = cls.get_by_id(case_id, lazy_load=True)
        if not case_old:
            return None

        existing_tickets = []
        for ticket in case_old.tickets or []:
            if isinstance(ticket, str):
                existing_tickets.append(ticket)
            elif ticket.rowid:
                existing_tickets.append(ticket.rowid)

        if ticket_rowid in existing_tickets:
            return ticket_rowid

        case_new = CaseModel()
        case_new.rowid = case_old.rowid
        case_new.tickets = [*existing_tickets, ticket_rowid]
        cls.update(case_new)

        return ticket_rowid


class Message(BaseWorksheetEntity[MessageModel]):
    """Message 实体类"""
    WORKSHEET_ID = "message"
    MODEL_CLASS = MessageModel


class Playbook(BaseWorksheetEntity[PlaybookModel]):
    """PlaybookLoader 实体类"""
    WORKSHEET_ID = "playbook"
    MODEL_CLASS = PlaybookModel

    @classmethod
    def get_by_id(cls, playbook_id, lazy_load=False) -> Union[PlaybookModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=playbook_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def list_pending_playbooks(cls) -> List[PlaybookModel]:
        """获取待处理的playbooks"""

        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="job_status",
                    operator=Operator.IN,
                    value=[PlaybookJobStatus.PENDING]
                )
            ]
        )

        return cls.list(filter_model, lazy_load=True)

    @classmethod
    def update_job_status_and_remark(cls, rowid: str, job_status: PlaybookJobStatus, remark: str) -> str:
        """更新 playbook 的 job_status 和 remark 字段

        Args:
            rowid: playbook 记录ID
            job_status: 新的作业状态
            remark: 备注信息

        Returns:
            更新后的记录ID
        """
        playbook_model_tmp = PlaybookModel()
        playbook_model_tmp.rowid = rowid
        playbook_model_tmp.job_status = job_status
        playbook_model_tmp.remark = remark

        rowid = Playbook.update(playbook_model_tmp)
        return rowid

    @classmethod
    def add_pending_playbook(cls, type: PlaybookType, name, user_input=None, source_rowid=None, record_id=None) -> PlaybookModel:
        if source_rowid is None:
            if record_id is None:
                raise Exception("id is required when source_rowid is None")
            else:
                if type == PlaybookType.CASE:
                    record = Case.get_by_id(record_id)
                    source_rowid = record.rowid
                elif type == PlaybookType.ALERT:
                    record = Alert.get_by_id(record_id)
                    source_rowid = record.rowid
                elif type == PlaybookType.ARTIFACT:
                    record = Artifact.get_by_id(record_id)
                    source_rowid = record.rowid

        model = PlaybookModel()
        model.source_rowid = source_rowid
        model.job_status = PlaybookJobStatus.PENDING
        model.type = type
        model.name = name
        model.user_input = user_input
        rowid = Playbook.create(model)
        model_create = Playbook.get(rowid, lazy_load=True)
        return model_create


class Knowledge(BaseWorksheetEntity[KnowledgeModel]):
    """PlaybookLoader 实体类"""
    WORKSHEET_ID = "knowledge"
    MODEL_CLASS = KnowledgeModel

    @classmethod
    def get_by_id(cls, knowledge_id, lazy_load=False) -> Union[KnowledgeModel, None]:
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="id",
                    operator=Operator.EQ,
                    value=knowledge_id
                )
            ]
        )
        result = cls.list(filter_model, lazy_load=lazy_load)
        if result:
            return result[0]
        else:
            return None

    @classmethod
    def list_undone_action_records(cls) -> List[KnowledgeModel]:
        """获取未完成的actions"""
        filter_model = Group(
            logic="AND",
            children=[
                Condition(
                    field="action",
                    operator=Operator.IN,
                    value=[KnowledgeAction.STORE, KnowledgeAction.REMOVE]
                )
            ]
        )
        return cls.list(filter_model)

    @classmethod
    def update_by_id(
            cls,
            knowledge_id: str,
            title: Union[str, None] = None,
            body: Union[str, None] = None,
            using: Union[bool, None] = None,
            action=None,
            source=None,
            tags: Union[List[str], None] = None
    ) -> Union[str, None]:
        knowledge_old = cls.get_by_id(knowledge_id, lazy_load=True)
        if not knowledge_old:
            return None

        knowledge_new = KnowledgeModel()
        knowledge_new.rowid = knowledge_old.rowid
        if title is not None:
            knowledge_new.title = title
        if body is not None:
            knowledge_new.body = body
        if using is not None:
            knowledge_new.using = using
        if action is not None:
            knowledge_new.action = action
        if source is not None:
            knowledge_new.source = source
        if tags is not None:
            knowledge_new.tags = tags

        return cls.update(knowledge_new)

    @classmethod
    def search(cls, query: Annotated[str, "The search query."]) -> Annotated[
        str, "relevant knowledge entries, policies, and special handling instructions."]:
        """
        Search the internal knowledge base for specific entities, business-specific logic, SOPs, or historical context.
        """
        logger.debug(f"knowledge search : {query}")
        embedding_client, collection_name = _get_embeddings_search_client()
        if embedding_client is None:
            logger.info("Knowledge search skipped because embeddings are disabled or unavailable.")
            return "[]"
        threshold = 0.5
        result_all = []
        docs_qdrant = embedding_client.search_documents_with_rerank(
            collection_name=collection_name,
            query=query,
            k=10,
            top_n=3,
        )
        logger.debug(docs_qdrant)
        for doc in docs_qdrant:
            if doc.metadata["rerank_score"] >= threshold:
                result_all.append(doc.page_content)

        results = json.dumps(result_all, ensure_ascii=False)
        logger.debug(f"Knowledge search results : {results}")
        return results


class Notice(object):
    @staticmethod
    def send(user: Union[AccountModel, List[AccountModel]], title, body=None):
        if isinstance(user, AccountModel):
            users = [user]
        elif isinstance(user, list):
            users = user
        else:
            logger.error("user 参数必须是 AccountModel 实例或 AccountModel 实例列表")
            return False
        for user in users:
            result = requests.post(SIRP_NOTICE_WEBHOOK, json={"title": title, "body": body, "user": user.fullname})
        return True
