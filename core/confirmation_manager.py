# CORE / confirmation_manager.py
# This class handles the pause/resume path for high-risk actions.
# Data flow is:
# pending confirmation lookup -> user reply check -> schema validation
# -> confirmed tool execution -> shared executor finalization

import json
import time

from core.tool_response import ToolResponse, ToolStatus
from repositories.confirmation_repository import ConfirmationRepository


class ConfirmationManager:
    async def handle(self, state, db, executor):
        repo = ConfirmationRepository(db)

        # 1) Check whether this user has a waiting confirmation at all.
        pending = await repo.get_pending(state.user_id)
        if not pending:
            return None

        reply = state.message.strip().lower()

        # 2) A rejection ends the pending action immediately and returns a direct reply.
        if reply == "no":
            await repo.mark_rejected(pending.confirmation_id)
            return {
                "run_id": None,
                "response": "Action cancelled as per your request.",
                "action": "confirmation",
            }

        # 3) Any reply other than yes/no keeps the confirmation open and asks again.
        if reply != "yes":
            return {
                "run_id": None,
                "response": "You have a pending confirmation. Please reply with 'yes' or 'no'.",
                "action": "confirmation",
            }

        # 4) Resolve the original tool from the executor registry so confirmed
        # execution uses the exact same tool definition and metadata as normal flow.
        tool = executor.tools_registry.get(pending.action)
        if not tool:
            return {
                "run_id": None,
                "response": f"Unknown action '{pending.action}'",
                "action": "confirmation",
            }

        parameters = pending.parameters

        # Stored parameters may come back as a JSON string depending on the DB path.
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except Exception:
                return {
                    "run_id": None,
                    "response": "Stored confirmation parameters are corrupted.",
                    "action": "confirmation",
                }

        # 5) Re-validate the stored params before execution. Confirmation should never
        # bypass the schema trust boundary.
        try:
            validated = tool.schema(**parameters)
        except Exception as e:
            return {
                "run_id": None,
                "response": f"Invalid parameters during confirmation. Details: {e}",
                "action": "confirmation",
            }

        # 6) Execute the tool under the same ToolResponse contract as normal execution.
        start = time.time()
        try:
            result = await tool.function(state.user_id, validated, db)

            if not isinstance(result, ToolResponse):
                raise TypeError(
                    f"Tool '{pending.action}' returned {type(result).__name__}, expected ToolResponse"
                )
        except Exception as e:
            latency_ms = round((time.time() - start) * 1000, 2)
            result = ToolResponse(
                status=ToolStatus.FAILED,
                message=f"Execution error: {str(e)}",
                error=str(e),
                metadata={"action": pending.action, "confirmed": True},
                latency_ms=latency_ms,
            )
        else:
            result.latency_ms = round((time.time() - start) * 1000, 2)
            result.metadata = result.metadata or {}
            result.metadata["confirmed"] = True

        # 7) Only after a real confirmed execution attempt do we close the pending request.
        await repo.mark_executed(pending.confirmation_id)

        # 8) Reuse the executor's shared finalization path so confirmed actions get
        # the same logging, outcomes, analysis, confidence, and response format.
        finalized = await executor.finalize_execution(
            state=state,
            db=db,
            tool=tool,
            action_name=pending.action,
            parameters=parameters,
            validated=validated,
            result=result,
        )
        finalized["action"] = "confirmation"
        return finalized
