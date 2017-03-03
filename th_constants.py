import collections

Endpoint = collections.namedtuple('Endpoint', 'url methods')
# four endpoints we call: /ready, /action/status, /action/done, /error all post
READY = Endpoint(url='/ready', methods=['POST'])
STATUS = Endpoint(url='/action/status', methods=['POST'])
DONE = Endpoint(url='/action/done', methods=['POST'])
ERROR = Endpoint(url='/error', methods=['POST'])
SHUTDOWN = Endpoint(url='/shutdown', methods=['POST'])
