import streamlit as st
import sympy as sp


def parse_function(expr_str):
    """Safely parse a user-entered function string using SymPy."""
    x = sp.Symbol("x")
    try:
        expr = sp.sympify(expr_str, locals={"x": x, "e": sp.E, "pi": sp.pi})
        return expr, x
    except Exception as e:
        raise ValueError(f"Could not parse expression: {e}")


def calculus_module():
    st.title("∫ Calculus")
    st.markdown(
        "Enter a mathematical function of **x** and explore limits, derivatives, and integrals symbolically."
    )

    st.info(
        "**Syntax tips:** Use `x` as the variable. "
        "Examples: `x**2 + 3*x - 5`, `sin(x)`, `exp(x)`, `log(x)`, `sqrt(x)`, `x**3/3`"
    )

    func_str = st.text_input("Enter f(x)", value="x**2 + 3*x - 5", placeholder="e.g. sin(x) + x**2")

    if not func_str.strip():
        st.warning("Please enter a function.")
        return

    try:
        expr, x = parse_function(func_str)
        st.latex(f"f(x) = {sp.latex(expr)}")
    except ValueError as e:
        st.error(str(e))
        return

    st.markdown("---")
    operation = st.radio(
        "Choose Operation",
        ["Limit", "Derivative", "Definite Integral", "Indefinite Integral"],
        horizontal=True,
    )

    st.markdown("---")

    if operation == "Limit":
        st.markdown("### Limit")
        col1, col2 = st.columns(2)
        with col1:
            point_str = st.text_input("x approaches", value="0", help="Can be a number, 'oo' for ∞, or '-oo'")
        with col2:
            direction = st.selectbox("Direction", ["Both sides (±)", "Right (+)", "Left (-)"])

        dir_map = {"Both sides (±)": "+", "Right (+)": "+", "Left (-)": "-"}
        dir_sym = dir_map[direction]

        if st.button("Compute Limit", type="primary"):
            try:
                if point_str.strip() in ("oo", "inf", "infinity"):
                    point = sp.oo
                elif point_str.strip() in ("-oo", "-inf", "-infinity"):
                    point = -sp.oo
                else:
                    point = sp.sympify(point_str)

                if direction == "Both sides (±)":
                    result = sp.limit(expr, x, point)
                    st.success("**Result:**")
                    st.latex(
                        rf"\lim_{{x \to {sp.latex(point)}}} f(x) = {sp.latex(result)}"
                    )
                else:
                    result = sp.limit(expr, x, point, dir_sym)
                    arrow = r"^+" if dir_sym == "+" else r"^-"
                    st.success("**Result:**")
                    st.latex(
                        rf"\lim_{{x \to {sp.latex(point)}{arrow}}} f(x) = {sp.latex(result)}"
                    )

                st.write(f"Numerical value: `{float(result):.6f}`" if result.is_real and result.is_finite else "")
            except Exception as e:
                st.error(f"Error computing limit: {e}")

    elif operation == "Derivative":
        st.markdown("### Derivative")
        order = st.slider("Order of derivative", 1, 5, 1)

        if st.button("Compute Derivative", type="primary"):
            try:
                deriv = sp.diff(expr, x, order)
                ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(order, f"{order}th")
                st.success("**Result:**")
                st.latex(
                    rf"\frac{{d^{order}}}{{dx^{order}}} f(x) = {sp.latex(deriv)}"
                    if order > 1
                    else rf"\frac{{d}}{{dx}} f(x) = {sp.latex(deriv)}"
                )
                st.write(f"**Simplified:** `{deriv}`")

                # Evaluate at a point
                st.markdown("#### Evaluate Derivative at a Point")
                eval_point = st.number_input("x =", value=0.0, format="%.4f", key="deriv_eval")
                try:
                    val = float(deriv.subs(x, eval_point))
                    st.metric(f"f'({eval_point})", f"{val:.6f}")
                except Exception:
                    st.info("Could not evaluate numerically at this point.")
            except Exception as e:
                st.error(f"Error computing derivative: {e}")

    elif operation == "Indefinite Integral":
        st.markdown("### Indefinite Integral")

        if st.button("Compute Integral", type="primary"):
            try:
                integral = sp.integrate(expr, x)
                st.success("**Result:**")
                st.latex(
                    rf"\int f(x)\,dx = {sp.latex(integral)} + C"
                )
                st.write(f"**Expression:** `{integral} + C`")
            except Exception as e:
                st.error(f"Error computing integral: {e}")

    elif operation == "Definite Integral":
        st.markdown("### Definite Integral")
        col1, col2 = st.columns(2)
        with col1:
            lower = st.text_input("Lower bound (a)", value="0")
        with col2:
            upper = st.text_input("Upper bound (b)", value="1")

        if st.button("Compute Definite Integral", type="primary"):
            try:
                a = sp.sympify(lower)
                b = sp.sympify(upper)
                result = sp.integrate(expr, (x, a, b))
                st.success("**Result:**")
                st.latex(
                    rf"\int_{{{sp.latex(a)}}}^{{{sp.latex(b)}}} f(x)\,dx = {sp.latex(result)}"
                )
                try:
                    st.metric("Numerical Value", f"{float(result):.8f}")
                except Exception:
                    st.info("Could not convert to a simple decimal (may be symbolic).")
            except Exception as e:
                st.error(f"Error computing definite integral: {e}")
