style(name="button") {
    font_color=(229,229,229)
    font_size=3%h
    normal {
        bg_color=(68,68,68)
    }
    hover {
        bg_color=(85,85,85)
    }
    press {
        bg_color=(45,45,45)
    }
}
style(name="disabled_button") {
    bg_color=(51,51,51)
    font_color=(107,114,128)
    font_size=3%h
}
style(name="primary_button") {
    font_color=(229,229,229)
    font_size=3%h
    normal {
        bg_color=(59,130,246)
    }
    hover {
        bg_color=(37,99,235)
    }
    pressed {
        bg_color=(29,78,216)
    }
}


group(name="all", anchor="center", bold=true) {
    group(name="tab_switch", bold=true, y=96%h, height=8%h, width=32%w, style="button") {
        button(
            text="<<Value1>>",
            x=16%w,
            tags=["tab_switch", "programs"]
        )
        button(
            text="<<Value2>>",
            x=50%w,
            width=36%w,
            tags=["tab_switch", "servers"]
        )
        button(
            text="<<Value3>>",
            x=84%w,
            style="disabled_button"
        )
    }

    button(
        text="Login",
        x=50%w, y=16%h,
        width=30%w, height=10%h,
        style="primary_button",
        tags=["login"]
    )
    button(
        text="Register",
        x=50%w, y=6%h,
        width=20%w, height=6%h,
        style="button",
        tags=["tab_switch", "register"]
    )


    group(name="fields", x=50%w, width=30%w, font_size=4%h) {
        input_text(
            y=35%h,
            height=8%h
        )
        input_text(
            y=60%h,
            height=8%h
        )
        group(name="field_labels", bold=true, text_color=(229,229,229), font_size=14) {
            label(
                text="Password",
                y=43%h,
            )
            label(
                text="Login",
                y=68%h,
            )
        }
    }
}
