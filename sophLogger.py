class SophLogger:
    def __init__(self, fileName):
        self.handle = open(fileName, "a")

    def __call__(self, something):
        try:
            text = "{0}\n".format(something)
            self.handle.write(text)
            self.handle.flush()
            print (text.strip())
        except:
            pass