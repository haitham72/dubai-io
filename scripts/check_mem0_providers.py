import mem0.configs.base as mb

print("Embedder providers in mem0:")
# inspect mem0 embedder configs
import mem0.embeddings.configs as ec
import pkgutil
import mem0.embeddings as me

for importer, modname, ispkg in pkgutil.iter_modules(me.__path__):
    print(" ", modname)

print("\nLLM providers in mem0:")
import mem0.llms as ml
for importer, modname, ispkg in pkgutil.iter_modules(ml.__path__):
    print(" ", modname)

print("\nVector store providers in mem0:")
import mem0.vector_stores as mv
for importer, modname, ispkg in pkgutil.iter_modules(mv.__path__):
    print(" ", modname)
