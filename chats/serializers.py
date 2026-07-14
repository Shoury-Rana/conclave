from rest_framework import serializers
from chats.models import ChatRooms, Messages

class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRooms
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = '__all__'