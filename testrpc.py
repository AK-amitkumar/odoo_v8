import xmlrpclib
url = 'http:///52.43.65.108:8069'
db = 'test_liricus'
username = 'admin'
password = 'Wineem2332'
common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
output = common.version()
print output
