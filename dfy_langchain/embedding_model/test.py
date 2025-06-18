from langchain_huggingface import HuggingFaceEmbeddings


embeddings = HuggingFaceEmbeddings(
    model_name=r"D:\ai\web_new\dfy_langchain\embedding_model\bce-embedding-base_v1",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)



print(embeddings)