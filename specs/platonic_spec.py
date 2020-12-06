from platonic import REST, URI

def testapp():
    app= REST(
        URI('hello',
            GET = None))
        
    assert len(app.uris) == 1
    assert app.uris[0].supports("GET")
    assert app.uris[0].supports("get")
    assert not app.uris[0].supports("POST")
    
testapp()
