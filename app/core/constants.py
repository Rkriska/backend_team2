import enum


class DocType(str, enum.Enum):
    TOR = "TOR"
    RAB = "RAB"
    ACUAN = "ACUAN"
    KEPMEN = "KEPMEN"
    SBM = "SBM"


class DocStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ChunkType(str, enum.Enum):
    PARAGRAF = "PARAGRAF"
    PASAL = "PASAL"


class ScreeningStage(str, enum.Enum):
    FORMAT = "FORMAT"
    SUBSTANSI = "SUBSTANSI"


class ScreeningStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FinalResult(str, enum.Enum):
    LOLOS = "LOLOS"
    REVISI = "REVISI"
    TIDAK_LOLOS = "TIDAK_LOLOS"


class LLMClassification(str, enum.Enum):
    LOLOS = "LOLOS"
    TIDAK_LOLOS = "TIDAK_LOLOS"
    PERLU_REVISI = "PERLU_REVISI"


# Qdrant collection names
COLLECTION_TOR = "tor_chunks"          # temporary per project
COLLECTION_REFERENCE = "reference_chunks"  # permanent regulatory docs
