def app(exp_func):
    def exp():
        exp_func()
    return exp