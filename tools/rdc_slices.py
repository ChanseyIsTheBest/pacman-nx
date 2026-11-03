# pacman-nx (2026-11-02): what a draw's textures hold, volume textures slice by slice (run inside qrenderdoc;
# tools/rdc_run.ps1 sets the environment). RDC_EVENTS = event ids. For each texture bound to the pixel shader: type,
# size, depth, mips, format, value range; PNGs of its first level (for a volume RDC_SLICES slices), and the raw bytes of
# a volume's first level (.bin) so a script can compare it with the PC's. Writes slices.txt.
import os
import traceback

import renderdoc as rd

IN = os.environ.get("RDC_IN")
OUT = os.environ.get("RDC_OUT")
EVENTS = [int(e) for e in os.environ.get("RDC_EVENTS", "").split(",") if e.strip()]
SLICES = [int(s) for s in os.environ.get("RDC_SLICES", "0,8,16,24,32,40,48,56,63").split(",")]
log = open(os.path.join(OUT, "slices.txt"), "w")


def say(*parts):
    log.write(" ".join(str(p) for p in parts) + "\n")
    log.flush()


def save_png(controller, t, slice_index, path):
    save = rd.TextureSave()
    save.resourceId = t.resourceId
    save.destType = rd.FileType.PNG
    save.alpha = rd.AlphaMapping.Discard
    save.mip = 0
    save.slice.sliceIndex = slice_index
    controller.SaveTexture(save, path)


try:
    cap = rd.OpenCaptureFile()
    if cap.OpenFile(IN, "", None) != rd.ResultCode.Succeeded:
        raise RuntimeError("open file")
    result = cap.OpenCapture(rd.ReplayOptions(), None)
    status, controller = result if isinstance(result, tuple) else (rd.ResultCode.Succeeded, result)
    textures = {t.resourceId: t for t in controller.GetTextures()}
    seen = set()
    for event in EVENTS:
        controller.SetFrameEvent(event, True)
        state = controller.GetPipelineState()
        say("event", event)
        for used in state.GetReadOnlyResources(rd.ShaderStage.Pixel, False):
            d = used.descriptor
            t = textures.get(d.resource)
            if not t:
                say("   index", used.access.index, "no texture")
                continue
            say("   index", used.access.index, "tex", int(d.resource), "type", str(t.type).split(".")[-1],
                "view", str(d.textureType).split(".")[-1], "%dx%dx%d arrays %d mips %d" % (t.width, t.height, t.depth, t.arraysize, t.mips),
                t.format.Name(), "view format", d.format.Name())
            if int(d.resource) in seen:
                continue
            seen.add(int(d.resource))
            if t.depth > 1:
                for s in SLICES:
                    if s >= t.depth:
                        continue
                    sub = rd.Subresource(0, s, 0)
                    lo, hi = controller.GetMinMax(d.resource, sub, rd.CompType.Typeless)
                    say("      slice", s, "min", ["%.3f" % v for v in lo.floatValue], "max", ["%.3f" % v for v in hi.floatValue])
                    save_png(controller, t, s, os.path.join(OUT, "tex%d_s%02d.png" % (int(d.resource), s)))
                data = controller.GetTextureData(d.resource, rd.Subresource(0, 0, 0))
                say("      level 0 bytes (first slice call)", len(data))
                with open(os.path.join(OUT, "tex%d.bin" % int(d.resource)), "wb") as f:
                    for s in range(t.depth):
                        f.write(bytes(controller.GetTextureData(d.resource, rd.Subresource(0, s, 0))))
            else:
                lo, hi = controller.GetMinMax(d.resource, rd.Subresource(0, 0, 0), rd.CompType.Typeless)
                say("      min", ["%.3f" % v for v in lo.floatValue], "max", ["%.3f" % v for v in hi.floatValue])
                save_png(controller, t, 0, os.path.join(OUT, "tex%d.png" % int(d.resource)))
    say("done")
except Exception:
    say(traceback.format_exc())
os._exit(0)
