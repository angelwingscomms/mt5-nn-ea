from __future__ import annotations

from .shared import *  # noqa: F401,F403

def export_onnx_model(model: nn.Module, dummy_input: torch.Tensor, output_path: Path) -> None:
    export_attempts = (
        ("legacy", {"dynamo": False}),
        ("dynamo", {"dynamo": True}),
    )
    last_error: Exception | None = None

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except ValueError:
                pass

    for exporter_name, exporter_kwargs in export_attempts:
        try:
            log.info("ONNX export | trying %s exporter (opset=14)", exporter_name)
            torch.onnx.export(
                model,
                (dummy_input,),
                str(output_path),
                input_names=["input"],
                output_names=["output"],
                opset_version=14,
                **exporter_kwargs,
            )
            log.info("ONNX export | succeeded with %s exporter", exporter_name)
            return
        except ModuleNotFoundError as exc:
            last_error = exc
            log.warning("ONNX export | %s exporter missing dependency: %s", exporter_name, exc)
        except Exception as exc:
            last_error = exc
            log.warning("ONNX export | %s exporter failed: %s", exporter_name, exc)

    if last_error is None:
        raise RuntimeError("ONNX export failed for an unknown reason.")
    raise RuntimeError(f"ONNX export failed with all available exporters: {last_error}") from last_error
