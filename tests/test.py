from app.services.llm import llm

res = llm.invoke("hello")
print(res.content)
