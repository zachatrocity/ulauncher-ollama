import json
import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


logger = logging.getLogger(__name__)


class OllamaExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def get_ollama_headers(self):
        headers = {}
        if self.preferences["ollama_headers"]:
            for header in self.preferences["ollama_headers"].split(","):
                header_key, header_value = header.split(":")
                headers[header_key.strip()] = header_value.strip()
        return headers

    def list_models(self):
        r = requests.get(
            self.preferences["ollama_host"] + "/api/tags",
            headers=self.get_ollama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise OllamaException("Error connecting to ollama.")

        models = []

        for m in response["models"]:
            if m and m["name"]:
                models.append(m["name"])

        return models

    def generate(self, event):

        logger.info(event)
        data = {
            "model": event['model'],
            "prompt": event['query'],
            "system": "You are an inline assitant, keep your responses short and sweet.",
            "stream": False
        }

        r = requests.post(
            self.preferences["ollama_host"] + "/api/generate",
            data=json.dumps(data),
            headers=self.get_ollama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise OllamaException(
                "Error connecting to ollama.")

        logger.debug(response)

        return response

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        # event is instance of ItemEnterEvent

        query = event.get_data()
        logger.debug(query)
        # do additional actions here...
        response = extension.generate(query)

        logger.debug(response)

        # you may want to return another list of results
        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/ollama.png", name="Ollama says..", description=response['response'], on_enter=CopyToClipboardAction()
                )
            ]
        )


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        models = extension.list_models()
        query = event.get_query().replace(extension.preferences["ollama_kw"] + " ", "")

        items = [
            ExtensionResultItem(
                icon="images/ollama.png",
                name="Ask default model...",
                description=query,
                on_enter=ExtensionCustomAction({"query": query, "model": extension.preferences["ollama_default_model"]}, keep_app_open=True),
            )
        ]

        for m in models:
            items.append(
                ExtensionResultItem(
                    icon="images/ollama.png",
                    name="Ask " + m + "...",
                    description=query,
                    on_enter=ExtensionCustomAction({"query": query, "model": m}, keep_app_open=True),
                )
            )

        return RenderResultListAction(items)


class OllamaException(Exception):
    """Exception thrown when there was an error calling the ollama API"""

    pass


if __name__ == "__main__":
    OllamaExtension().run()
