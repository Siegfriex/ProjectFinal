"""out_of_unit — required positional structural arg whose nested key is read unguarded.
Not an 'optional-key access' (no .get / no guard), so pass (a) must find 0 sites here and pass (b) must list it."""


def score(features):
    return features["envelope"]["raw"] * 2
