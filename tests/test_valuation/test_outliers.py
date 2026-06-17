from valuation.outliers import filter_iqr


def test_empty_list():
    assert filter_iqr([]) == []


def test_below_threshold_unchanged():
    assert filter_iqr([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]


def test_clean_values_unchanged():
    values = [10.0, 11.0, 12.0, 13.0, 14.0]
    assert sorted(filter_iqr(values)) == sorted(values)


def test_clear_outlier_removed():
    values = [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0]
    result = filter_iqr(values)
    assert 1000.0 not in result
    assert len(result) == 5


def test_all_same_values_retained():
    values = [50.0] * 6
    assert filter_iqr(values) == values


def test_low_outlier_removed():
    values = [-1000.0, 10.0, 11.0, 12.0, 13.0, 14.0]
    result = filter_iqr(values)
    assert -1000.0 not in result
