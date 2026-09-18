from utils.helpers import safe_filename

def test_safe_filename():
    assert safe_filename('Ali / Khan') == 'Ali_Khan'
