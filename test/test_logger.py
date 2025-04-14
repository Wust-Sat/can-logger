import can_logger.logger as l

def test_fields():
    x = l.Logger()
    assert x.test == "test"
