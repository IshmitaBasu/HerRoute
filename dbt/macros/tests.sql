{% test coverage_range(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < 0 or {{ column_name }} > 100)
{% endtest %}

{% test nonnegative_when_known(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and {{ column_name }} < 0
{% endtest %}

{% test valid_wkt(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} is null
   or try(ST_GeometryFromText({{ column_name }})) is null
{% endtest %}
