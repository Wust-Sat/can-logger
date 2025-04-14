import can_logger.logger as l

x = l.Logger()

assert x.test == "test"

x.echo()
