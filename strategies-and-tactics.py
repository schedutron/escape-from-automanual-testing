""" (this file is problem set two of three)


This file contains problems that are designed to expose you to the
`hypothesis.strategies` API and a variety of techniques for composing
or adjusting strategies for your tests.

Key link:  https://hypothesis.readthedocs.io/en/latest/data.html


"""

import json

import pytest
import random
import hypothesis
from hypothesis import given, settings, strategies as st, reproduce_failure


##############################################################################
# Practicing with the `.filter(...)` method

# Remove the mark.xfail decorator,
# then improve the filter function to make the test pass.

@given(st.integers().filter(lambda x: x % 2 == 0))
def test_filter_even_numbers(x):
    # If we convert any even integer to a string, the last digit will be even.
    assert str(x)[-1] in "02468"


@given(st.integers().filter(lambda x: x % 2 == 1))
def test_filter_odd_numbers(x):
    # If we convert any odd integer to a string, the last digit will be odd.
    assert str(x)[-1] in "13579"


# Takeaway
# --------
# While `.filter` was used here to the same effect as `.map` below,
# it should be noted that filtering should not be relied on to reject
# large populations of generated values. Hypothesis will raise if
# a strategy ends up filtering too many values in attempt to generate
# permissible ones.
#
# Suppose you want to generate all integers except 0, this is a perfect
# application of `.filter`:
#    `st.integers().filter(lambda x: x != 0)`


##############################################################################
# Practicing with the `.map(...)` method
# Same tasks as above, without using .filter(...).
# You'll need to change the value of the integer, then convert it to a string.


@given(st.integers().map(lambda x: str(2*x)))
def test_map_even_numbers(x):
    # Check that last character of string x is a substring of "02468"
    assert x[-1] in "02468"


@given(st.integers().map(lambda x: str(2*x + 1)))
def test_map_odd_numbers(x):
    assert x[-1] in "13579"


# Takeaway
# --------
# `.map` permits us to extend Hypothesis' core strategies in powerful
# ways. See that it can be used to affect the individual values being
# produced by a strategy (e.g. mapping integers to even-valued
# integers), as well as to cast the values to a different type (e.g.
# mapping an integer to a string.
#
# If it seems like a data-type is missing from Hypothesis'
# strategies, then it is likely that a simple application of `.map`
# will suffice. E.g. suppose you want a strategy that generate deques,
# then
#     `deque_strat = st.lists(...).map(deque)`
# will serve nicely - we don't even need a lambda!


##############################################################################
# Defining recursive data.

# There are a couple of ways to define recursive data with Hypothesis,
# leaning on the fact that strategies are lazily instantiated.
#
# `st.recursive` takes a base strategy, and a function that takes a strategy
# and returns an extended strategy.  All good if we want that structure!
# If you want mutual recursion though, or have a complicated kind of data
# (or just limited time in a tutorial), `st.deferred` is the way to go.
#
# The `Record` exercise in pbt-101.py defined JSON using `st.recursive`,
# if you want to compare them, and has some extension problems that you
# could write as tests here instead.


# JSON values are defined as one of null, false, true, a finite number,
# a string, an array of json values, or a dict of string to json values.
json_strat = st.deferred(
    lambda: st.one_of(
        st.none(),
        st.booleans(),
        # TODO: Write out the rest of this definition in Hypothesis strategies!
        st.integers(),
        st.floats(allow_nan=False),
        st.text(),
        st.lists(json_strat),
        st.dictionaries(st.text(), json_strat)
    )
)

# If in doubt, you can copy-paste the definition of json_strat to an interactive
# prompt, and use the `.example()` method of the strategy to see what kind of
# data it generates.  Be warned though!  The distribution of `.example()`s is
# skewed towards simple options, and it should only ever be used interactively.


# You can use `@settings(verbosity=hypothesis.Verbosity.verbose)` (or `debug`,
# or `pytest -s --hypothesis-verbosity=verbose`) to see what's going on,
# or get a summary with the `hypothesis.event(message)` function and
# `pytest --hypothesis-show-statistics ...`

@given(json_strat)
def test_json_dumps(value):
    """Checks that value is serialisable as JSON."""
    # We expect this test to always pass - the point of this exercise is
    # to define a recursive strategy, and then investigate the values it
    # generates for a *passing* test.
    hypothesis.note("type: {}".format(type(value)))
    hypothesis.event("type: {}".format(type(value)))
    json.dumps(value)


# Takeaway: you've seen and played with a few ways to see what a
# passing test is doing, without having to inject a failure.


##############################################################################
# `@st.composite` exercise

# This goal of this exercise is to play with a contrived data dependency,
# using a composite strategy to generate inputs.  You can use the same tricks
# as above to check what's being generated, so try to keep the test passing!


@st.composite
def a_composite_strategy(draw):
    """Generates a (List[int], index) pair.  The index points to a random positive
    element (>= 1); if there are no positive elements index is None.

    `draw` is used within a composite strategy as, e.g.::

        >>> draw(st.booleans()) # can draw True or False
        True

    Note that `draw` is a reserved parameter that will be used by the
    `st.composite` decorator to interactively draw values from the
    strategies that you invoke within this function. That is, you need
    not pass a value to `draw` when calling this strategy::

       >>> a_composite_strategy().example()
       ([-1, -2, -3, 4], 3)
    """
    # TODO: draw a list, determine the allowed indices, and choose one to return
    lst = draw(st.lists(st.integers()))

    indices = st.integers(min_value=0, max_value=max(0, len(lst)-1)).filter(lambda x: lst[x] > 0 if lst else False)
    index = draw(indices) #.example()  # Doesn't work
    '''
    allowed_indices = []
    for i, num in enumerate(lst):
        if num > 0:
            allowed_indices.append(i)
    if allowed_indices:
        index = random.choice(allowed_indices)
    '''
    # TODO: determine the list of allowed indices, and choose one if non-empty
    return (lst, index)


@given(a_composite_strategy())
def test_a_composite_strategy(value):
    lst, index = value
    assert all(isinstance(n, int) for n in lst)
    if index is None:
        assert all(n < 1 for n in lst)
    else:
        assert lst[index] >= 1


# Takeaway
# --------
# Why generate a tuple with a `@composite` strategy instead of using two
# separate strategies?  This way we can ensure certain relationships between
# the `lst` and `index` values!  (You can get a similar effect with st.data(),
# but the reporting and reproducibility isn't as nice.)

##############################################################################
# Simplified json-schema inference

# Note: you are not expected to finish this optional extension!

# One really useful pattern for complex data is to infer a strategy from an
# existing schema of some kind. For example, Hypothesis ships with functions
# for inference from types, regular expressions, Numpy dtypes, etc.
#
# This exercise is to write a function that, given a simple "json-schema",
# returns a strategy for objects that will match that schema (details below).
#
# We'll use a simplified subset of the specification today, but there is a
# real-world version here:  https://pypi.org/project/hypothesis-jsonschema/
#
# Final tip: I suggest starting by adding any tests, then improving the
# schema_strategy and check_schema functions, *then* strengthening the
# validate and from_schema functions. You might be surprised!


SCHEMA_TYPES = tuple(["null"]*3 + ["bool"]*3 + ["number"]*3 + ["string"]*3 + ["array"])
print(SCHEMA_TYPES)


def check_schema(schema):
    """A helper function to check whether something is a valid schema."""
    # Much simpler than the real spec - every schema must have a type,
    # only one numeric type, and no objects.
    assert isinstance(schema, dict)
    type_ = schema.get("type")
    assert type_ in SCHEMA_TYPES, schema
    if type_ in ("null", "bool"):
        assert len(schema) == 1  # No other keys allowed
    # TODO: number: check maximum and minimum, no other keys
    elif type_ == "number":
        assert set(schema).issubset("type minimum maximum".split())
        if "minimum" in schema:
            minimum = schema["minimum"]
            assert isinstance(minimum, float), type(minimum)
        if "maximum" in schema:
            maximum = schema["maximum"]
            assert isinstance(maximum, float), type(maximum)
        if "minimum" in schema and "maximum" in schema:
            assert minimum <= maximum

    elif type_ == "string":
        assert set(schema).issubset("type minLength maxLength".split())
        # TODO: check the values of maxLength and minLength are positive
        # and correctly ordered - *if* the keys are present at all!
        if "minLength" in schema:
            minLength = schema["minLength"]
            assert isinstance(minLength, int), type(minLength)
            assert minLength >= 0, minLength
        if "maxLength" in schema:
            maxLength = schema["maxLength"]
            assert isinstance(maxLength, int), type(maxLength)
            assert maxLength >= 0, maxLength
        if "minLength" in schema and "maxLength" in schema:
            assert minLength <= maxLength
    else:  # For arrays
        # TODO: array: check maxLength and minLength, items schema, no other keys
        assert "items_schema" in schema, schema
        assert set(schema).issubset("type minLength maxLength items_schema".split())
        if "minLength" in schema:
            minLength = schema["minLength"]
            assert isinstance(minLength, int), type(minLength)
            assert minLength >= 0, minLength
        if "maxLength" in schema:
            maxLength = schema["maxLength"]
            assert isinstance(maxLength, int), type(maxLength)
            assert maxLength >= 0, maxLength
        if "minLength" in schema and "maxLength" in schema:
            assert minLength <= maxLength
        check_schema(schema["items_schema"]), schema["items_schema"]
            
    #       (bonus round: support uniqueItems for arrays with JSON round-trip)


def validate(schema, instance):
    """Return True if `instance` matches `schema`, otherwise False."""
    check_schema(schema)
    if schema.get("type") == "null":
        return instance is None
    if schema.get("type") == "bool":
        return isinstance(instance, bool)
    if schema.get("type") == "number":
        return (
            isinstance(instance, float) and schema.get(
                "minimum", float("-inf")
            ) <= instance <= schema.get("maximum", float("inf")))
    # TODO: complete length validation checks for string and array
    if schema.get("type") == "string":
        return isinstance(instance, type(u"")) and schema.get(
            "minLength", 0
        ) <= len(instance) <= schema.get("maxLength", float("inf"))
    # For array:
    return isinstance(instance, list) and schema.get(
        "minLength", 0
    ) <= len(instance) <= len(instance) <= schema.get("maxLength", float("inf"))
    for ele in instance:
        validate(schema["items_schema"], ele)

@st.composite
def from_schema(draw, schema):
    """Returns a strategy for objects that match the given schema."""
    check_schema(schema)
    # TODO: actually handle constraints on number/string/array schemas
    type_ = schema["type"]
    if type_ == "null":
        return draw(st.none())
    if type_ == "bool":
        return draw(st.booleans())
    if type_ == "number":
        return draw(st.floats(
            allow_nan=False, min_value=schema.get("minimum"), max_value=schema.get("maximum")))
    if type_ == "string":
        return draw(st.text(min_size=schema.get("minLength"), max_size=schema.get("maxLength")))
    # For arrays:
    return draw(
        st.lists(
            from_schema(schema["items_schema"]),
            min_size=schema.get("minLength"),
            max_size=schema.get("maxLength")
            )
        )


# `@st.composite` is one way to write this - another would be to define a
# bare function, and `return st.one_of(st.none(), st.booleans(), ...)` so
# each strategy can be defined individually. Use whichever seems more
# natural to you - the important thing in tests is usually readability!
@st.composite
def schema_strategy(draw):
    schema = {"type": draw(st.sampled_from(SCHEMA_TYPES))}
    # TODO: generate constraints on number/string/array schemas
    # (hint: can you design this so they shrink to less constrained?)
    if schema["type"] in ("null", "bool"):
        pass
    elif schema["type"] == "number":
        if random.getrandbits(1):
            schema["minimum"] = draw(st.floats(allow_nan=False))
        if random.getrandbits(1):
            schema["maximum"] = draw(st.floats(min_value=schema.get("minimum")))
    elif schema["type"] == "string":
        if random.getrandbits(1):
            schema["minLength"] = draw(st.integers(min_value=0))
        if random.getrandbits(1):
            schema["maxLength"] = draw(st.integers(min_value=schema.get("minLength", 0)))
    else:  # For arrays:
        if random.getrandbits(1):
            schema["minLength"] = draw(st.integers(min_value=0))
        if random.getrandbits(1):
            schema["maxLength"] = draw(st.integers(min_value=schema.get("minLength", 0)))
        schema["items_schema"] = draw(schema_strategy())
    return schema


@settings(deadline=None)  # allow for slower tests with large data
@given(st.data(), schema_strategy())
def test_schema_inference(data, schema):
    # Test that we can always generate a valid instance
    instance = data.draw(from_schema(schema))
    assert validate(schema, instance)


# TODO: write a test that shows validate may return False (maybe a unit test!)
@given(st.data(), st.just({'items_schema': {'type': 'array', 'items_schema': {'type': 'number'}}, 'minLength': 1, 'type': 'array'}))
def test_validation(data, schema):
    instance = data.draw(from_schema(schema))
    assert validate(schema, instance)
