async def world(context, *args, **kwargs):
    await context["koduck"].sendmessage(context["message"], sendcontent="world")