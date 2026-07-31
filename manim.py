from manim import *
class Yoink(Scene):
    def construct(self):
        t = Text("Yoink")
        self.play(Write(t))
