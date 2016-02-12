# Originally from https://gist.github.com/hSATAC/3300699

def request(context, flow):
  if "example.com" in flow.request.host:
    if flow.request.scheme == "https":
      flow.request.host = "192.168.254.9"
      flow.request.port = "50113"
    if flow.request.scheme == "http":
      flow.request.host = "192.168.254.9"
      flow.request.port = "50110"
