"""
MCP-Flow Protocol Animation

Generates an animated diagram showing the MCP-Flow protocol communication.

Usage:
    pip install manim
    manim -pql mcp_flow_animation.py McpFlowDiagram --format=gif

For higher quality:
    manim -pqh mcp_flow_animation.py McpFlowDiagram --format=gif
"""

from manim import *


class McpFlowDiagram(Scene):
    def construct(self):
        # Colors
        CLIENT_COLOR = "#3B82F6"  # Blue
        SERVER_COLOR = "#10B981"  # Green
        CONTROL_COLOR = "#F59E0B"  # Amber
        STREAM_COLOR = "#8B5CF6"  # Purple
        DATAGRAM_COLOR = "#EC4899"  # Pink

        # Title
        title = Text("MCP-Flow Protocol", font_size=36, color=WHITE)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.8)

        # Client and Server boxes
        client_box = RoundedRectangle(
            corner_radius=0.2, width=2.5, height=1.2, color=CLIENT_COLOR
        )
        client_box.shift(LEFT * 4.5)
        client_label = Text("Client", font_size=24, color=CLIENT_COLOR)
        client_label.move_to(client_box)

        server_box = RoundedRectangle(
            corner_radius=0.2, width=2.5, height=1.2, color=SERVER_COLOR
        )
        server_box.shift(RIGHT * 4.5)
        server_label = Text("Server", font_size=24, color=SERVER_COLOR)
        server_label.move_to(server_box)

        # Vertical lines for sequence diagram
        client_line = DashedLine(
            start=client_box.get_bottom() + DOWN * 0.2,
            end=client_box.get_bottom() + DOWN * 5,
            color=CLIENT_COLOR,
            dash_length=0.1,
        )
        server_line = DashedLine(
            start=server_box.get_bottom() + DOWN * 0.2,
            end=server_box.get_bottom() + DOWN * 5,
            color=SERVER_COLOR,
            dash_length=0.1,
        )

        self.play(
            Create(client_box),
            Create(server_box),
            Write(client_label),
            Write(server_label),
            run_time=0.6,
        )
        self.play(Create(client_line), Create(server_line), run_time=0.4)

        # Helper function to create animated message
        def send_message(start_x, end_x, y, label_text, color, is_dashed=False):
            start = np.array([start_x, y, 0])
            end = np.array([end_x, y, 0])

            if is_dashed:
                arrow = DashedLine(start, end, color=color, dash_length=0.15)
                tip = Triangle(color=color, fill_opacity=1).scale(0.1)
                tip.move_to(end)
                tip.rotate(0 if end_x > start_x else PI)
                arrow = VGroup(arrow, tip)
            else:
                arrow = Arrow(start, end, color=color, buff=0, stroke_width=3)

            label = Text(label_text, font_size=16, color=color)
            label.next_to(arrow, UP, buff=0.1)

            # Animate packet moving along the arrow
            dot = Dot(color=color, radius=0.08)
            dot.move_to(start)

            self.play(GrowArrow(arrow) if not is_dashed else Create(arrow), Write(label), run_time=0.3)
            self.play(dot.animate.move_to(end), run_time=0.4)
            self.play(FadeOut(dot), run_time=0.1)

            return VGroup(arrow, label)

        # Control Stream label
        control_label = Text("Control Stream", font_size=14, color=CONTROL_COLOR)
        control_label.shift(UP * 0.5 + LEFT * 0.5)
        self.play(Write(control_label), run_time=0.3)

        # Message sequence
        y_pos = -0.3

        # 1. Initialize request
        msg1 = send_message(-3.2, 3.2, y_pos, "initialize", CONTROL_COLOR)
        y_pos -= 0.8

        # 2. Initialize response
        msg2 = send_message(3.2, -3.2, y_pos, "result + transport caps", CONTROL_COLOR)
        y_pos -= 0.8

        # 3. Tools call
        msg3 = send_message(-3.2, 3.2, y_pos, "tools/call", CONTROL_COLOR)
        y_pos -= 0.6

        # Execution Stream label
        stream_label = Text("Execution Stream", font_size=14, color=STREAM_COLOR)
        stream_label.shift(DOWN * 1.8 + LEFT * 0.5)
        self.play(Write(stream_label), run_time=0.3)

        # 4. Bulk data stream (thick line with multiple packets)
        y_pos -= 0.4
        stream_start = np.array([3.2, y_pos, 0])
        stream_end = np.array([-3.2, y_pos, 0])
        stream_arrow = Arrow(
            stream_start, stream_end, color=STREAM_COLOR, buff=0, stroke_width=6
        )
        stream_text = Text("bulk data", font_size=16, color=STREAM_COLOR)
        stream_text.next_to(stream_arrow, UP, buff=0.1)

        # Multiple packets animation
        packets = VGroup()
        for i in range(4):
            packet = Square(side_length=0.2, color=STREAM_COLOR, fill_opacity=0.8)
            packet.move_to(stream_start)
            packets.add(packet)

        self.play(GrowArrow(stream_arrow), Write(stream_text), run_time=0.3)
        
        # Animate packets in parallel (showing no HoL blocking)
        self.play(
            *[packets[i].animate.move_to(stream_end + RIGHT * (i * 0.3)) for i in range(4)],
            run_time=0.6,
            lag_ratio=0.15,
        )
        self.play(FadeOut(packets), run_time=0.2)

        y_pos -= 0.8

        # 5. Response with stream reference
        msg5 = send_message(3.2, -3.2, y_pos, "response + ref/stream", CONTROL_COLOR)
        y_pos -= 0.6

        # Datagram label
        dg_label = Text("Datagrams (unreliable)", font_size=14, color=DATAGRAM_COLOR)
        dg_label.shift(DOWN * 3.5 + LEFT * 0.2)
        self.play(Write(dg_label), run_time=0.3)

        y_pos -= 0.4

        # 6. Datagrams (dotted, showing progress updates)
        for i, text in enumerate(["progress 25%", "progress 50%", "progress 100%"]):
            start = np.array([3.2, y_pos, 0])
            end = np.array([-3.2, y_pos, 0])
            
            dashed = DashedLine(start, end, color=DATAGRAM_COLOR, dash_length=0.1)
            tip = Triangle(color=DATAGRAM_COLOR, fill_opacity=1).scale(0.08)
            tip.move_to(end + RIGHT * 0.1)
            tip.rotate(PI)
            
            label = Text(text, font_size=14, color=DATAGRAM_COLOR)
            label.next_to(dashed, UP, buff=0.05)
            
            dot = Dot(color=DATAGRAM_COLOR, radius=0.06)
            dot.move_to(start)
            
            self.play(Create(dashed), Create(tip), Write(label), run_time=0.2)
            self.play(dot.animate.move_to(end), run_time=0.25)
            self.play(FadeOut(dot), run_time=0.05)
            
            y_pos -= 0.4

        # Final highlight box
        self.wait(0.5)
        
        highlight_box = SurroundingRectangle(
            VGroup(stream_arrow, stream_text),
            color=STREAM_COLOR,
            buff=0.15,
            stroke_width=2,
        )
        highlight_text = Text(
            "No head-of-line blocking!",
            font_size=18,
            color=STREAM_COLOR,
        )
        highlight_text.next_to(highlight_box, DOWN, buff=0.2)
        
        self.play(Create(highlight_box), Write(highlight_text), run_time=0.5)
        self.wait(1)

        # Fade out
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.8)


class McpComparison(Scene):
    """Side-by-side comparison: Traditional MCP vs MCP-Flow."""
    
    def construct(self):
        # Colors
        BLUE = "#3B82F6"
        GREEN = "#10B981"
        AMBER = "#F59E0B"
        PURPLE = "#8B5CF6"
        RED = "#EF4444"
        GRAY = "#6B7280"

        # =====================================================================
        # LEFT SIDE: Traditional MCP (with HoL blocking)
        # =====================================================================
        left_title = Text("Traditional MCP", font_size=24, color=RED)
        left_title.shift(LEFT * 3.5 + UP * 3)
        
        left_client = Text("Client", font_size=18, color=BLUE)
        left_client.shift(LEFT * 5 + UP * 2.2)
        left_server = Text("Server", font_size=18, color=GREEN)
        left_server.shift(LEFT * 2 + UP * 2.2)
        
        left_c_line = Line(LEFT * 5 + UP * 1.9, LEFT * 5 + DOWN * 2.8, color=BLUE, stroke_width=2)
        left_s_line = Line(LEFT * 2 + UP * 1.9, LEFT * 2 + DOWN * 2.8, color=GREEN, stroke_width=2)

        # =====================================================================
        # RIGHT SIDE: MCP-Flow (parallel streams)
        # =====================================================================
        right_title = Text("MCP-Flow", font_size=24, color=GREEN)
        right_title.shift(RIGHT * 3.5 + UP * 3)
        
        right_client = Text("Client", font_size=18, color=BLUE)
        right_client.shift(RIGHT * 2 + UP * 2.2)
        right_server = Text("Server", font_size=18, color=GREEN)
        right_server.shift(RIGHT * 5 + UP * 2.2)
        
        right_c_line = Line(RIGHT * 2 + UP * 1.9, RIGHT * 2 + DOWN * 2.8, color=BLUE, stroke_width=2)
        right_s_line = Line(RIGHT * 5 + UP * 1.9, RIGHT * 5 + DOWN * 2.8, color=GREEN, stroke_width=2)

        # Divider
        divider = DashedLine(UP * 3, DOWN * 3, color=GRAY, dash_length=0.2)

        # Draw setup
        self.play(
            Write(left_title), Write(right_title),
            Create(divider),
            run_time=0.5
        )
        self.play(
            Write(left_client), Write(left_server),
            Write(right_client), Write(right_server),
            Create(left_c_line), Create(left_s_line),
            Create(right_c_line), Create(right_s_line),
            run_time=0.4
        )

        # Helper for arrows
        def make_arrow(x1, x2, y, color, text, is_left=True):
            offset = LEFT * 3.5 if is_left else RIGHT * 3.5
            start = np.array([x1, y, 0]) + offset
            end = np.array([x2, y, 0]) + offset
            arr = Arrow(start, end, color=color, buff=0, stroke_width=2, max_tip_length_to_length_ratio=0.15)
            lbl = Text(text, font_size=12, color=color)
            lbl.next_to(arr, UP, buff=0.05)
            return arr, lbl

        # =====================================================================
        # ANIMATION: Show the difference
        # =====================================================================
        
        y = 1.5
        
        # Both: Request 1
        arr_l1, lbl_l1 = make_arrow(-1.5, 1.5, y, AMBER, "request 1", True)
        arr_r1, lbl_r1 = make_arrow(-1.5, 1.5, y, AMBER, "request 1", False)
        self.play(GrowArrow(arr_l1), Write(lbl_l1), GrowArrow(arr_r1), Write(lbl_r1), run_time=0.3)
        
        y -= 0.5
        
        # Both: Large response starts
        # LEFT: Single stream, blocks everything
        # RIGHT: Separate execution stream
        
        arr_l2, lbl_l2 = make_arrow(1.5, -1.5, y, RED, "large response...", True)
        arr_r2, lbl_r2 = make_arrow(1.5, -1.5, y, PURPLE, "stream: data", False)
        self.play(GrowArrow(arr_l2), Write(lbl_l2), GrowArrow(arr_r2), Write(lbl_r2), run_time=0.3)
        
        y -= 0.5
        
        # LEFT: Still sending large response (blocking)
        # RIGHT: Can send control message in parallel!
        arr_l3, lbl_l3 = make_arrow(1.5, -1.5, y, RED, "...still sending...", True)
        arr_r3, lbl_r3 = make_arrow(-1.5, 1.5, y, AMBER, "request 2", False)
        
        # Show blocking on left
        block_text = Text("BLOCKED", font_size=14, color=RED)
        block_text.shift(LEFT * 5 + DOWN * 0.3)
        
        self.play(
            GrowArrow(arr_l3), Write(lbl_l3),
            GrowArrow(arr_r3), Write(lbl_r3),
            Write(block_text),
            run_time=0.4
        )
        
        y -= 0.5
        
        # LEFT: More blocking
        # RIGHT: Response 2 comes back immediately
        arr_l4, lbl_l4 = make_arrow(1.5, -1.5, y, RED, "...waiting...", True)
        arr_r4, lbl_r4 = make_arrow(1.5, -1.5, y, AMBER, "response 2", False)
        self.play(GrowArrow(arr_l4), Write(lbl_l4), GrowArrow(arr_r4), Write(lbl_r4), run_time=0.3)
        
        y -= 0.5
        
        # LEFT: Finally done
        # RIGHT: Stream completes
        arr_l5, lbl_l5 = make_arrow(1.5, -1.5, y, RED, "...done", True)
        arr_r5, lbl_r5 = make_arrow(1.5, -1.5, y, PURPLE, "stream: done", False)
        self.play(GrowArrow(arr_l5), Write(lbl_l5), GrowArrow(arr_r5), Write(lbl_r5), run_time=0.3)
        
        y -= 0.5
        
        # LEFT: Now can send request 2
        # RIGHT: Already done!
        arr_l6, lbl_l6 = make_arrow(-1.5, 1.5, y, AMBER, "request 2 (delayed!)", True)
        done_text = Text("Done!", font_size=16, color=GREEN)
        done_text.shift(RIGHT * 3.5 + DOWN * 1.8)
        
        self.play(GrowArrow(arr_l6), Write(lbl_l6), Write(done_text), run_time=0.3)
        
        # Final labels
        self.wait(0.3)
        
        hol_label = Text("Head-of-Line Blocking", font_size=16, color=RED)
        hol_label.shift(LEFT * 3.5 + DOWN * 2.5)
        
        parallel_label = Text("Parallel Streams", font_size=16, color=GREEN)
        parallel_label.shift(RIGHT * 3.5 + DOWN * 2.5)
        
        self.play(Write(hol_label), Write(parallel_label), run_time=0.4)
        
        self.wait(1.5)


class McpFlowSimple(Scene):
    """Simpler, cleaner version for README."""
    
    def construct(self):
        # Colors
        BLUE = "#3B82F6"
        GREEN = "#10B981"
        AMBER = "#F59E0B"
        PURPLE = "#8B5CF6"
        PINK = "#EC4899"

        # Client and Server
        client = Text("Client", font_size=28, color=BLUE)
        client.shift(LEFT * 4 + UP * 2.5)
        
        server = Text("Server", font_size=28, color=GREEN)
        server.shift(RIGHT * 4 + UP * 2.5)

        # Vertical lines
        c_line = Line(LEFT * 4 + UP * 2, LEFT * 4 + DOWN * 3, color=BLUE, stroke_width=2)
        s_line = Line(RIGHT * 4 + UP * 2, RIGHT * 4 + DOWN * 3, color=GREEN, stroke_width=2)

        self.play(Write(client), Write(server), run_time=0.4)
        self.play(Create(c_line), Create(s_line), run_time=0.3)

        def arrow_with_packet(y, text, color, reverse=False):
            x1, x2 = (-3.8, 3.8) if not reverse else (3.8, -3.8)
            arr = Arrow([x1, y, 0], [x2, y, 0], color=color, buff=0, stroke_width=2)
            lbl = Text(text, font_size=16, color=color)
            lbl.next_to(arr, UP, buff=0.08)
            
            dot = Dot(color=color, radius=0.1)
            dot.move_to([x1, y, 0])
            
            self.play(GrowArrow(arr), Write(lbl), run_time=0.25)
            self.play(dot.animate.move_to([x2, y, 0]), run_time=0.35)
            self.remove(dot)
            return VGroup(arr, lbl)

        # Sequence
        arrow_with_packet(1.3, "initialize", AMBER)
        arrow_with_packet(0.6, "result", AMBER, reverse=True)
        arrow_with_packet(-0.1, "tools/call", AMBER)
        
        # Bulk stream - thicker, multiple dots
        y = -0.9
        bulk = Arrow([3.8, y, 0], [-3.8, y, 0], color=PURPLE, buff=0, stroke_width=5)
        bulk_lbl = Text("bulk data stream", font_size=16, color=PURPLE)
        bulk_lbl.next_to(bulk, UP, buff=0.08)
        
        dots = VGroup(*[Dot(color=PURPLE, radius=0.08) for _ in range(5)])
        for d in dots:
            d.move_to([3.8, y, 0])
        
        self.play(GrowArrow(bulk), Write(bulk_lbl), run_time=0.25)
        self.play(
            *[dots[i].animate.move_to([-3.8 + i*0.2, y, 0]) for i in range(5)],
            run_time=0.5,
            lag_ratio=0.1
        )
        self.remove(dots)
        
        arrow_with_packet(-1.6, "response", AMBER, reverse=True)
        
        # Datagrams
        for i, pct in enumerate(["progress...", "progress...", "done"]):
            y = -2.2 - i * 0.45
            arr = DashedLine([3.8, y, 0], [-3.8, y, 0], color=PINK, dash_length=0.15)
            lbl = Text(pct, font_size=14, color=PINK)
            lbl.next_to(arr, UP, buff=0.05)
            dot = Dot(color=PINK, radius=0.06)
            dot.move_to([3.8, y, 0])
            self.play(Create(arr), Write(lbl), run_time=0.15)
            self.play(dot.animate.move_to([-3.8, y, 0]), run_time=0.2)
            self.remove(dot)

        self.wait(1.5)
