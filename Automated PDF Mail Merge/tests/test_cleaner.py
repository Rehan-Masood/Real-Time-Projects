import pandas as pd
from core.data_cleaner import clean_and_validate

def test_cleaner():
    df = pd.DataFrame([{'employee_id':'1','name':'Ali','salary':'Rs. 85,000'}])
    out, report = clean_and_validate(df)
    assert out.loc[0, 'salary'] == '85000'
    assert report['valid_rows'] == 1
