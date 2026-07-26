import streamlit as st

from cadena import responder_pregunta

st.set_page_config(page_title="Agente BimBam Buy", page_icon="🛒", layout="centered")

st.title("🛒 Agente de IA — BimBam Buy")

if "historial" not in st.session_state:
    st.session_state.historial = []
    
with st.sidebar:

    st.header("ℹ️ Información")

    st.write(
        """
Este asistente responde utilizando únicamente
la documentación oficial de **BimBam Buy**.
"""
    )

    st.divider()

    st.write("Documentación disponible:")

    st.markdown("""
- Reembolsos
- Garantías
- Pagos
- Envíos
- Programa de afiliados
""")

    if st.button("🗑️ Nueva conversación", use_container_width=True):
        st.session_state.historial = []
        st.rerun()

if not st.session_state.historial:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(
            """
Hola 👋

Soy el asistente virtual de **BimBam Buy**.

Puedo ayudarte con consultas sobre:

- 💳 Métodos de pago
- 🚚 Envíos
- 🔄 Reembolsos y devoluciones
- 🛡️ Garantías
- 🤝 Programa de afiliados

Escribe tu consulta en el cuadro inferior.
"""
        )



# Mostrar historial de la conversación
for mensaje in st.session_state.historial:
    avatar = "👤" if mensaje["rol"] == "user" else "🤖"
    with st.chat_message(mensaje["rol"], avatar=avatar):
        st.markdown(mensaje["contenido"])

        if mensaje.get("fuentes"):
            with st.expander("📄 Documentos utilizados"):
                for fuente in mensaje["fuentes"]:
                    st.markdown(f"- {fuente}")

# Input del usuario
pregunta = st.chat_input("Escribí tu pregunta sobre políticas de BimBam Buy...")

if pregunta:
    st.session_state.historial.append({"rol": "user", "contenido": pregunta})
    with st.chat_message("user", avatar="👤"):
        st.markdown(pregunta)

    with st.chat_message("assistant", avatar="🤖"):

        with st.spinner("Analizando la documentación..."):

            try:
                resultado = responder_pregunta(pregunta)

                st.markdown(resultado["respuesta"])

                if resultado["fuentes"]:
                    with st.expander("📄 Documentos utilizados"):
                        for fuente in resultado["fuentes"]:
                            st.markdown(f"- {fuente}")

            except Exception:
                st.error(
                    "Ocurrió un error al consultar la base documental."
                )
                st.stop()

    st.session_state.historial.append(
        {
            "rol": "assistant",
            "contenido": resultado["respuesta"],
            "fuentes": resultado["fuentes"],
        }
    )


