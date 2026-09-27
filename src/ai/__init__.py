"""Module ``ai`` — couche IA d'ORIONIS.

Contient l'abstraction LLM (``ai.llm``) interchangeable et les utilitaires
de prompt (``ai.prompts``). Les analystes IA (étape 05) s'appuient sur
cette couche pour générer des décisions de trading autonomes.

La vision d'ORIONIS stipule explicitement : « La couche IA doit être
interchangeable. » C'est le rôle de ``LLMProvider`` : tous les analystes
dépendent de l'interface, jamais d'un provider spécifique.
"""
