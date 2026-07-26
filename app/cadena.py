"""
Cadena RAG del agente de BimBam Buy.

Carga el índice FAISS generado por `ingesta.py`, recupera los fragmentos más
relevantes y prioriza automáticamente el documento que obtuvo la mayor
similitud antes de enviar el contexto al LLM.
"""

import os
from pathlib import Path
from collections import defaultdict

from pydantic import BaseModel, Field

from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

load_dotenv()

CARPETA_INDICE = Path(__file__).parent.parent / "indice_faiss"

MODELO_EMBEDDINGS = "intfloat/multilingual-e5-small"
MODELO_LLM = "llama-3.3-70b-versatile"

class RespuestaRAG(BaseModel):
    respuesta: str = Field(
        description="Respuesta para el usuario."
    )

    fuentes: list[str] = Field(
        description="Lista de documentos realmente utilizados para responder."
    )

output_parser = PydanticOutputParser(
    pydantic_object=RespuestaRAG
)

PROMPT_SISTEMA = """
Eres el asistente virtual de BimBam Buy.

Responde únicamente utilizando el contexto proporcionado.

Reglas:

- Usa únicamente información del contexto. 
- Incluye únicamente los documentos que realmente utilizaste.
- No inventes información.
- Si el contexto no contiene información suficiente responde exactamente: "No encontré esta información en los documentos disponibles."

{format_instructions}

Contexto:

{contexto}
"""

_vectorstore = None
_cadena = None


def _cargar_vectorstore():
    global _vectorstore

    if _vectorstore is not None:
        return _vectorstore

    if not CARPETA_INDICE.exists():
        raise FileNotFoundError(
            f"No existe {CARPETA_INDICE}. Ejecuta primero ingesta.py"
        )

    embeddings = HuggingFaceEmbeddings(
        model_name=MODELO_EMBEDDINGS
    )

    _vectorstore = FAISS.load_local(
        str(CARPETA_INDICE),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    return _vectorstore


def _cargar_cadena():

    global _cadena

    if _cadena is not None:
        return _cadena

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "No se encontró GROQ_API_KEY."
        )

    llm = ChatGroq(
        api_key=api_key,
        model_name=MODELO_LLM,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                PROMPT_SISTEMA,
            ),
            (
                "human",
                "{pregunta}",
            ),
        ]
    ).partial(
        format_instructions=output_parser.get_format_instructions()
    )

    _cadena = prompt | llm | output_parser

    return _cadena


def recuperar_fragmentos(vectorstore, pregunta, k=8):
    """
    Recupera los k fragmentos más similares junto con su score.
    """

    resultados = vectorstore.similarity_search_with_score(
        f"query: {pregunta}",
        k=k,
    )

    return resultados


def priorizar_documento(resultados):
    """
    Agrupa los fragmentos por documento.

    Calcula una puntuación de evidencia usando los 3 fragmentos
    más similares de cada documento y devuelve todos los
    fragmentos ordenados priorizando el documento con mayor
    evidencia.
    """

    grupos = defaultdict(list)

    for doc, score in resultados:
        archivo = doc.metadata.get("archivo", "desconocido")
        grupos[archivo].append((doc, score))

    ranking = []

    for archivo, lista in grupos.items():

        # Menor score = mayor similitud.
        # Convertimos cada score en una "fuerza" de evidencia.
        lista.sort(key=lambda x: x[1])

        mejores = lista[:3]

        evidencia = sum(
            1 / (score + 1e-6)
            for _, score in mejores
        )

        ranking.append(
            (
                evidencia,
                archivo,
                lista,
            )
        )

    ranking.sort(
        key=lambda x: x[0],
        reverse=True
    )

    fragmentos_ordenados = []

    for _, _, lista in ranking:
        fragmentos_ordenados.extend(
            [doc for doc, _ in lista]
        )

    return fragmentos_ordenados


def responder_pregunta(pregunta: str):

    vectorstore = _cargar_vectorstore()

    cadena = _cargar_cadena()

    resultados = recuperar_fragmentos(
        vectorstore,
        pregunta,
        k=8,
    )

    if not resultados:

        return {
            "respuesta": "No encontré esta información en los documentos disponibles.",
            "fuentes": [],
        }

    fragmentos = priorizar_documento(resultados)

    contexto = "\n\n".join(

        f"[Fuente: {doc.metadata.get('archivo')}]\n{doc.page_content}"

        for doc in fragmentos
    )


    try:
        resultado = cadena.invoke(
            {
                "pregunta": pregunta,
                "contexto": contexto,
            }
        )
    except OutputParserException:
        return {
            "respuesta": "No encontré esta información en los documentos disponibles.",
            "fuentes": [],
        }

    return {
        "respuesta": resultado.respuesta,
        "fuentes": resultado.fuentes,
    }