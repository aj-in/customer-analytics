

## AI Customer Analytics

> **AI Vector Embedding to extract specific product issues from Google Reviews API.**
 
**Live demo →** [arjun-kakade-customer-analytics.streamlit.app](https://arjun-kakade-customer-analytics.streamlit.app/)

<img width="2424" height="1395" alt="image" src="https://github.com/user-attachments/assets/af996d27-3ec8-4b8c-89a2-a6375461ddc7" />


<br>

## Why this project exists

Late responses to negative reviews erode trust. Ops teams can't read 200+ reviews across 4+ branches every week. Most go uncategorized, unanswered, unresolved.

> **We lose customers we'll never know we lost** — driven away by unresolved negative reviews.

I developed an AI clustering model in Python to catch issues *before* they gain negative traction, enabling Operations teams prioritize time-sensitive product issues.

<br>
<br>

## What it does, in three minutes

The dashboard does three things, in order:

**1. Pulls reviews automatically.**
Scheduled API refreshes via AWS Glue. No more weekly *export → download → switch site → repeat*. Hours of data-entry tax eliminated per branch, every week.

**2. Groups complaints by meaning, not keywords.**
A SQL query `WHERE review LIKE '%loud%'` returns **0 matches** against my dataset. The AI returns **twelve** — because *"jackhammer"*, *"thin walls"*, and *"doors slamming"* all describe the same problem.

**3. Surfaces what to act on.**
Top 5 complaints by volume, slowest issues to resolve, CSAT trendline, and a live ops ticket queue with one-click resolve.

<br>
<br>

## Engineering challenges I had to think through

<br>


**Clusters were initially unreadable.** First pass auto-labeled groups *"Anniversary / Breakfast / Dinner"* — technically right, but are barely actionable to a manager.

> **Fix:** each cluster centroid now cosine-matches against a curated label library e.g. `Slow Check-in`, `Hidden Fees`, `Construction Noise`. Dashboards now say things ops can act on.

<img width="1924" height="940" alt="image" src="https://github.com/user-attachments/assets/b2a54864-9c46-4186-8beb-518a9c44ea40" />

<br>
<br>



**Resolved tickets weren't refreshing the dashboard.** I was reloading from disk on every render, which meant slow, laggy metrics.

> **Fix:** moved the data flow into `session_state` and committed to SQL database on the same call. Resolve a ticket → every metric updates instantly. *(real-time updates)*

**Had to hide API keys** in admin panel and not push it to direct AWS Glue, preventing data leaks/lawsuits. In real-world I would look at AWS Secretes Manager to do that


<img width="1880" height="1030" alt="image" src="https://github.com/user-attachments/assets/a54e6fa7-654b-485c-a105-68e1f18cd5d8" />


<br>
<br>

## Why this works for any business

The pipeline treats the data source as a parameter. **No manual if-then rules.** Point it at:

- **Customer reviews** → top issues, fixed faster, higher CSAT
- **Support tickets** → operational pain points ranked by volume and impact
- **Survey free-text or Glassdoor pages** → product or culture signal

**Competitor analysis is the ultimate use case.** Feed in a competitor's public reviews. Sales walks into the next pitch with *"Here's what their customers complain about. Here's how we don't."*

<br>
<br>

## What's next



The model currently struggles with truly mixed reviews — *"loved the product, hated the staff."* The **Uncategorizable** tab already flags these with a confidence score for ops to override in one click.

> **Future Scope:** feed every partially negative review back into unresolved issues, to ensure no unresolved errors.
