from knowledge_compiler.schemas import AnswerTrace
from knowledge_compiler.storage import WorkspaceStore


def trace_last_answer(*, store: WorkspaceStore) -> AnswerTrace:
    return store.trace_last_answer()
