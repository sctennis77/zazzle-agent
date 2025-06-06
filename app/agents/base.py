from abc import ABC, abstractmethod

class ChannelAgent(ABC):
    @abstractmethod
    def post_content(self, product, content):
        pass

    @abstractmethod
    def interact_with_users(self, product, context=None):
        pass 