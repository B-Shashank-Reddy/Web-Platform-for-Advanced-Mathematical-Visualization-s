import streamlit as st
import numpy as np


def matrix_module():
    st.title(" Matrix Operations")
    st.markdown("Enter a matrix and choose an operation to perform.")

    # Matrix size selector
    col1, col2 = st.columns(2)
    with col1:
        rows = st.number_input("Number of Rows", min_value=1, max_value=6, value=2, step=1)
    with col2:
        cols = st.number_input("Number of Columns", min_value=1, max_value=6, value=2, step=1)

    rows, cols = int(rows), int(cols)

    st.markdown("#### Enter Matrix A")
    matrix_input = []
    for i in range(rows):
        row_cols = st.columns(cols)
        row = []
        for j, c in enumerate(row_cols):
            val = c.number_input(
                f"A[{i+1}][{j+1}]",
                value=0.0,
                key=f"a_{i}_{j}",
                label_visibility="collapsed",
                format="%.4f",
            )
            row.append(val)
        matrix_input.append(row)

    A = np.array(matrix_input)

    st.markdown("#### Matrix A")
    st.dataframe(A, use_container_width=False)

    st.markdown("---")
    st.markdown("#### Choose Operations")

    ops = st.multiselect(
        "Select one or more operations",
        ["Determinant", "Inverse", "Rank", "Transpose", "Trace", "Eigenvalues"],
        default=["Determinant"],
    )

    # Second matrix for addition/multiplication
    show_b = st.checkbox("Add a second Matrix B (for addition / multiplication)")
    B = None
    if show_b:
        st.markdown("#### Enter Matrix B")
        matrix_b_input = []
        for i in range(rows):
            row_cols = st.columns(cols)
            row = []
            for j, c in enumerate(row_cols):
                val = c.number_input(
                    f"B[{i+1}][{j+1}]",
                    value=0.0,
                    key=f"b_{i}_{j}",
                    label_visibility="collapsed",
                    format="%.4f",
                )
                row.append(val)
            matrix_b_input.append(row)
        B = np.array(matrix_b_input)
        st.dataframe(B, use_container_width=False)

        b_ops = st.multiselect(
            "Operations involving A and B",
            ["A + B", "A - B", "A × B"],
            default=["A + B"],
        )
    else:
        b_ops = []

    if st.button("Compute", type="primary"):
        st.markdown("---")
        st.markdown("### Results")

        for op in ops:
            with st.expander(f"**{op}**", expanded=True):
                try:
                    if op == "Determinant":
                        if rows != cols:
                            st.error("Determinant is only defined for square matrices.")
                        else:
                            det = np.linalg.det(A)
                            st.metric("det(A)", f"{det:.6f}")
                            if abs(det) < 1e-10:
                                st.warning("⚠️ Determinant is ~0 → Matrix is singular (non-invertible).")

                    elif op == "Inverse":
                        if rows != cols:
                            st.error("Inverse is only defined for square matrices.")
                        else:
                            det = np.linalg.det(A)
                            if abs(det) < 1e-10:
                                st.error("Matrix is singular — inverse does not exist.")
                            else:
                                inv = np.linalg.inv(A)
                                st.write("A⁻¹ =")
                                st.dataframe(np.round(inv, 6))

                    elif op == "Rank":
                        rank = np.linalg.matrix_rank(A)
                        st.metric("Rank of A", rank)

                    elif op == "Transpose":
                        st.write("Aᵀ =")
                        st.dataframe(A.T)

                    elif op == "Trace":
                        if rows != cols:
                            st.error("Trace is only defined for square matrices.")
                        else:
                            trace = np.trace(A)
                            st.metric("tr(A)", f"{trace:.6f}")

                    elif op == "Eigenvalues":
                        if rows != cols:
                            st.error("Eigenvalues are only defined for square matrices.")
                        else:
                            eigenvalues, eigenvectors = np.linalg.eig(A)
                            st.write("**Eigenvalues:**")
                            for i, ev in enumerate(eigenvalues):
                                if np.isreal(ev):
                                    st.write(f"λ{i+1} = {ev.real:.6f}")
                                else:
                                    st.write(f"λ{i+1} = {ev:.6f}")
                            st.write("**Eigenvectors (columns):**")
                            st.dataframe(np.round(eigenvectors, 6))

                except Exception as e:
                    st.error(f"Error computing {op}: {e}")

        for op in b_ops:
            with st.expander(f"**{op}**", expanded=True):
                try:
                    if B is None:
                        st.error("Matrix B not provided.")
                    elif op == "A + B":
                        if A.shape != B.shape:
                            st.error("Matrices must have the same dimensions for addition.")
                        else:
                            st.write("A + B =")
                            st.dataframe(A + B)
                    elif op == "A - B":
                        if A.shape != B.shape:
                            st.error("Matrices must have the same dimensions for subtraction.")
                        else:
                            st.write("A - B =")
                            st.dataframe(A - B)
                    elif op == "A × B":
                        if A.shape[1] != B.shape[0]:
                            st.error(f"Cannot multiply: A is {A.shape}, B is {B.shape}. Columns of A must equal rows of B.")
                        else:
                            st.write("A × B =")
                            st.dataframe(np.dot(A, B))
                except Exception as e:
                    st.error(f"Error computing {op}: {e}")
