select
    count(*) as total_active_flights,
    count(*) filter (where on_ground) as on_ground_count,
    count(distinct origin_country) as countries_represented,
    round(avg(velocity)::numeric, 1) as avg_velocity_ms,
    max(fetched_at) as last_updated_at
from {{ ref('current_flights') }}
