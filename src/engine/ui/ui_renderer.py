import numpy as np
import moderngl
from pathlib import Path

class UIRenderer:
    def __init__(
        self,
        ctx: moderngl.Context,
        ui_tex: moderngl.Texture
    ) -> None:
        self.ctx = ctx
        self.ui_tex = ui_tex

        cwd = Path(__file__).parent
        frag_path = cwd.parent.parent / "shaders" / "ui" / "frag.frag"
        vert_path = cwd.parent.parent / "shaders" / "ui" / "vert.vert"

        self.vert_src = vert_path.read_text(encoding="utf-8")
        self.frag_src = frag_path.read_text(encoding="utf-8")
        self.ui_prog = self.ctx.program(vertex_shader=self.vert_src, fragment_shader=self.frag_src)

        self.verts = np.array([
           -1,  1, 0, 0,
           -1, -1, 0, 1,
            1,  1, 1, 0,
            1, -1, 1, 1,
        ], dtype="f4")
        self.vbo = self.ctx.buffer(self.verts)
        self.vao = self.ctx.vertex_array(self.ui_prog, [(self.vbo, "2f 2f", "in_vert", "in_texcoord")])  # type: ignore
