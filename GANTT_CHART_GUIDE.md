# Gantt Chart Guide

Complete guide for creating project timeline visualizations with Gantt charts in pandastable.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Data Format](#data-format)
3. [Gantt Chart Options](#gantt-chart-options)
4. [Step-by-Step Instructions](#step-by-step-instructions)
5. [Example Use Cases](#example-use-cases)
6. [Customization](#customization)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 3-Step Process

**Step 1: Prepare Data**
Create a CSV with at least these columns:
- `Task`: Task name
- `Start`: Start date (YYYY-MM-DD format)
- `End`: End date OR `Duration`: Duration in days

**Step 2: Load in pandastable**
```bash
python examples/csv_browser_v6.x1.2_search_columns.py
```

**Step 3: Create Gantt Chart**
- Load your CSV file
- Click **Plot** button
- Select **'gantt'** plot type
- Click **Apply Options**

---

## Data Format

### Required Columns

| Column | Required | Format | Description |
|--------|----------|--------|-------------|
| **Task** | ✅ Yes | Text | Task name or description |
| **Start** | ✅ Yes | Date | Start date (YYYY-MM-DD, MM/DD/YYYY, etc.) |
| **End** | ⚠️ One of | Date | End date (if Duration not provided) |
| **Duration** | ⚠️ One of | Number | Duration in days (if End not provided) |

**Note:** You must provide either `End` or `Duration` (or both).

### Optional Columns

| Column | Format | Description | Example |
|--------|--------|-------------|---------|
| **Progress** | Number (0-100) | Task completion percentage | 75 |
| **Status** | Text | Task status for color coding | "In Progress" |
| **Phase** | Text | Project phase for grouping | "Phase 1" |
| **Owner** | Text | Task owner/assignee | "Alice" |

### Column Name Variations

The Gantt chart recognizes these column name variations (case-insensitive):

**Task Column:**
- `Task`, `task`, `Task_Name`, `task_name`, `Name`, `name`

**Start Date:**
- `Start`, `start`, `Start_Date`, `start_date`, `Begin`, `begin`

**End Date:**
- `End`, `end`, `End_Date`, `end_date`, `Finish`, `finish`

**Duration:**
- `Duration`, `duration`, `Days`, `days`

**Progress:**
- `Progress`, `progress`, `Complete`, `complete`, `Completion`, `completion`

**Status:**
- `Status`, `status`, `State`, `state`

---

## Gantt Chart Options

### Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **show progress** | Checkbox | ✓ On | Show progress bars within tasks |
| **show today** | Checkbox | ✓ On | Show vertical line for today's date |
| **date format** | Dropdown | %Y-%m-%d | Date format for X-axis labels |
| **bar height** | Slider | 0.8 | Height of task bars (0.3-1.0) |
| **show milestones** | Checkbox | ✓ On | Show milestone markers (future) |
| **group by** | Entry | "" | Column name to group tasks by |
| **sort by** | Dropdown | start_date | Sort tasks by this criterion |

### Date Format Options

| Format | Example | Description |
|--------|---------|-------------|
| `%Y-%m-%d` | 2025-01-15 | ISO format (default) |
| `%m/%d/%Y` | 01/15/2025 | US format |
| `%d/%m/%Y` | 15/01/2025 | European format |
| `%b %d` | Jan 15 | Month abbreviation |
| `%Y-%m` | 2025-01 | Year-Month only |

### Sort By Options

| Option | Description |
|--------|-------------|
| **start_date** | Sort by start date (earliest first) |
| **end_date** | Sort by end date |
| **task_name** | Sort alphabetically by task name |
| **duration** | Sort by task duration (shortest first) |
| **none** | No sorting (use original order) |

---

## Step-by-Step Instructions

### Method 1: Using CSV Browser

**1. Start CSV Browser**
```bash
cd c:\Users\juesh\jules\pandastable0
python examples\csv_browser_v6.x1.2_search_columns.py
```

**2. Load Gantt Data**
- Navigate to the directory with your CSV
- Click on the CSV file (e.g., `gantt_example_1_simple.csv`)
- Data appears in the right panel

**3. Open Plot Viewer**
- Click the **Plot** button in the toolbar
- Plot viewer window opens

**4. Select Gantt Chart**
- Find the **"kind"** dropdown
- Select **"gantt"** from the list
- Gantt options section appears

**5. Configure Options**

Scroll to the **"gantt"** section:
- ✅ **show progress**: Checked (shows completion bars)
- ✅ **show today**: Checked (shows today's date line)
- **date format**: Select `%Y-%m-%d` (or your preference)
- **bar height**: Adjust slider (0.8 default)
- **sort by**: Select `start_date`
- **group by**: Leave blank (or enter column name like "Phase")

**6. Generate Chart**
- Click **"Apply Options"** button
- Gantt chart displays

### Method 2: Using DataExplore

**1. Start DataExplore**
```bash
python pandastable\app.py
```

**2. Import CSV**
- Click **File → Import → CSV**
- Select your Gantt data file
- Click **Open**

**3. Create Chart**
- Click **Tools → Plot**
- Select **'gantt'** plot type
- Configure options
- Click **"Apply Options"**

---

## Example Use Cases

### Example 1: Simple Project Timeline

**File:** `gantt_example_1_simple.csv`

**Data Structure:**
```csv
Task,Start,End,Progress,Status
Project Planning,2025-01-01,2025-01-15,100,Complete
Requirements Gathering,2025-01-10,2025-01-25,100,Complete
Design Phase,2025-01-20,2025-02-10,80,In Progress
Development - Backend,2025-02-01,2025-03-15,50,In Progress
...
```

**Settings:**
```
Plot type: gantt
show progress: On
show today: On
date format: %Y-%m-%d
sort by: start_date
```

**Result:**
- 8 tasks displayed chronologically
- Progress bars show completion (green = complete, blue = in progress)
- Today line shows current date
- Color-coded by status

**Use Case:** Basic project tracking, sprint planning

---

### Example 2: Duration-Based Planning

**File:** `gantt_example_2_duration.csv`

**Data Structure:**
```csv
Task,Start,Duration,Progress,Status,Owner
Kickoff Meeting,2025-01-05,1,100,Complete,Alice
Market Research,2025-01-06,10,100,Complete,Bob
...
```

**Features:**
- Uses `Duration` instead of `End` date
- Includes `Owner` column for assignment tracking
- 16 tasks with varying durations

**Settings:**
```
Plot type: gantt
show progress: On
show today: On
sort by: start_date
group by: Owner
```

**Result:**
- Tasks grouped by owner
- Duration automatically calculated
- Progress visualization
- Owner-based organization

**Use Case:** Resource allocation, team workload visualization

---

### Example 3: Multi-Phase Project

**File:** `gantt_example_3_phases.csv`

**Data Structure:**
```csv
Task,Start,End,Progress,Status,Phase
Requirements Workshop,2025-01-02,2025-01-05,100,Complete,Phase 1 - Planning
Architecture Design,2025-01-10,2025-01-20,100,Complete,Phase 2 - Design
Backend Setup,2025-01-25,2025-02-05,80,In Progress,Phase 3 - Development
...
```

**Features:**
- 23 tasks across 5 project phases
- Phase-based grouping
- Detailed status tracking

**Settings:**
```
Plot type: gantt
show progress: On
show today: On
sort by: start_date
group by: Phase
colormap: tab10
```

**Result:**
- Tasks grouped by phase
- Color-coded by status
- Clear phase progression
- Progress tracking per task

**Use Case:** Large project management, waterfall methodology, phase gates

---

### Example 4: Agile Sprint Planning

**Create Your Own:**
```csv
Task,Start,Duration,Progress,Status,Sprint
User Story 1,2025-01-08,5,100,Complete,Sprint 1
User Story 2,2025-01-08,3,100,Complete,Sprint 1
User Story 3,2025-01-10,5,80,In Progress,Sprint 1
User Story 4,2025-01-15,5,60,In Progress,Sprint 2
User Story 5,2025-01-15,3,40,In Progress,Sprint 2
User Story 6,2025-01-18,5,20,Not Started,Sprint 2
```

**Settings:**
```
Plot type: gantt
show progress: On
show today: On
sort by: start_date
group by: Sprint
bar height: 0.6
```

**Use Case:** Agile sprint planning, story tracking, burndown visualization

---

### Example 5: Construction Project

**Create Your Own:**
```csv
Task,Start,End,Progress,Status,Contractor
Site Preparation,2025-02-01,2025-02-15,100,Complete,ABC Construction
Foundation,2025-02-10,2025-03-05,90,In Progress,XYZ Builders
Framing,2025-03-01,2025-03-25,50,In Progress,ABC Construction
Plumbing,2025-03-15,2025-04-10,20,Not Started,PlumbCo
Electrical,2025-03-20,2025-04-15,10,Not Started,ElectriTech
Drywall,2025-04-05,2025-04-25,0,Not Started,ABC Construction
Finishing,2025-04-20,2025-05-15,0,Not Started,FinishPro
```

**Settings:**
```
Plot type: gantt
show progress: On
show today: On
date format: %b %d
sort by: start_date
group by: Contractor
```

**Use Case:** Construction scheduling, contractor coordination, critical path

---

## Customization

### Color Coding by Status

The Gantt chart automatically assigns colors based on the `Status` column:

**Default Colors:**
- **Complete**: Green
- **In Progress**: Blue
- **Not Started**: Gray
- **Delayed**: Red
- **On Hold**: Yellow

**Custom Status Values:**
You can use any status names. The chart will assign unique colors automatically.

### Progress Visualization

**Progress Bar Behavior:**
- **0%**: Empty bar (light color)
- **1-99%**: Partial fill (darker color overlay)
- **100%**: Full bar (solid color)

**Disable Progress:**
- Uncheck **"show progress"** option
- All bars show as full (no progress indication)

### Grouping Tasks

**Group by Phase:**
```
group by: Phase
```

**Group by Owner:**
```
group by: Owner
```

**Group by Department:**
```
group by: Department
```

**Effect:**
- Tasks are sorted first by group, then by start date
- Visual separation between groups
- Easier to see team/phase workload

### Date Range Control

**Automatic Range:**
- Chart automatically spans from earliest start to latest end
- Includes padding for readability

**Manual Range:**
- Filter your data before plotting
- Only include tasks in desired date range

---

## Troubleshooting

### Issue: "Gantt chart requires at least Task and Start columns"

**Cause:** Required columns not found

**Solutions:**
1. Ensure you have a column named `Task` (or `task`, `Name`, etc.)
2. Ensure you have a column named `Start` (or `start`, `Start_Date`, etc.)
3. Check column names are spelled correctly
4. Check for extra spaces in column names

---

### Issue: "Could not parse start dates"

**Cause:** Date format not recognized

**Solutions:**
1. Use standard date formats:
   - `YYYY-MM-DD` (2025-01-15)
   - `MM/DD/YYYY` (01/15/2025)
   - `DD/MM/YYYY` (15/01/2025)
2. Ensure all dates are in the same format
3. Check for typos in dates
4. Remove any text from date columns

---

### Issue: "Could not calculate end dates from duration"

**Cause:** Duration column has non-numeric values

**Solutions:**
1. Ensure Duration column contains only numbers
2. Remove any text (like "days", "weeks")
3. Convert weeks to days (1 week = 7 days)
4. Check for empty cells in Duration column

---

### Issue: Tasks appear in wrong order

**Cause:** Sort option not set correctly

**Solutions:**
1. Set **sort by** to `start_date` for chronological order
2. Use `task_name` for alphabetical order
3. Use `duration` to see shortest tasks first
4. Use `none` to keep original CSV order

---

### Issue: Progress bars not showing

**Cause:** Progress option disabled or no Progress column

**Solutions:**
1. Check **"show progress"** is enabled
2. Ensure you have a `Progress` column in your data
3. Verify Progress values are between 0 and 100
4. Check Progress column has numeric values (not text)

---

### Issue: Today line not visible

**Cause:** Today's date outside chart range

**Solutions:**
1. Ensure your project includes today's date
2. Check **"show today"** is enabled
3. Verify your system date is correct
4. Extend project timeline to include current date

---

### Issue: Colors all the same

**Cause:** No Status column or all same status

**Solutions:**
1. Add a `Status` column to your data
2. Use different status values (Complete, In Progress, etc.)
3. Ensure Status column has varying values
4. Check Status column is not empty

---

### Issue: Task names truncated

**Cause:** Task names too long for display

**Solutions:**
1. Shorten task names in your CSV
2. Use abbreviations
3. Increase figure size in plot options
4. Rotate task labels (future feature)

---

## Advanced Features

### Calculating Project Duration

**Total Project Duration:**
```python
# In your CSV, add a summary row
Total Duration = Latest End Date - Earliest Start Date
```

**Critical Path:**
- Identify tasks with 0 slack time
- Highlight with special status
- Sort by start date to see sequence

### Dependency Visualization

**Current:** Not directly supported

**Workaround:**
1. Name tasks with sequence numbers (1.1, 1.2, etc.)
2. Use Status to indicate blocked tasks
3. Group related tasks by Phase

**Future:** Arrow connections between dependent tasks

### Resource Leveling

**View Resource Allocation:**
1. Use `group by: Owner`
2. Look for overlapping bars
3. Identify overallocation

**Balance Workload:**
- Adjust start dates to prevent overlap
- Reassign tasks to other team members
- Extend durations if needed

---

## Best Practices

### Data Preparation

**1. Consistent Date Format**
- Use ISO format (YYYY-MM-DD) for reliability
- Avoid mixed formats in same column

**2. Meaningful Task Names**
- Keep names concise but descriptive
- Use consistent naming convention
- Include task IDs if needed

**3. Realistic Durations**
- Include buffer time
- Account for dependencies
- Consider resource availability

**4. Regular Updates**
- Update Progress column weekly
- Adjust dates as needed
- Update Status to reflect reality

### Visualization Tips

**1. Limit Number of Tasks**
- 20-30 tasks per chart maximum
- Break large projects into phases
- Create separate charts for each phase

**2. Use Grouping Effectively**
- Group by Phase for waterfall projects
- Group by Owner for resource view
- Group by Sprint for agile projects

**3. Color Coding**
- Use consistent status names
- Limit to 5-7 status types
- Choose meaningful names (not just colors)

**4. Date Range**
- Show 2-4 months at a time
- Include past for context
- Extend to next milestone

---

## Integration with Other Tools

### Export Options

**Save as Image:**
- Right-click on plot
- Select "Save Image"
- Choose PNG, PDF, or SVG format

**Copy to Clipboard:**
- Use screenshot tool
- Paste into presentations
- Include in reports

### Update from Project Management Tools

**From MS Project:**
1. Export to CSV
2. Map columns (Task, Start, Finish → End)
3. Add Progress and Status columns
4. Load in pandastable

**From Jira:**
1. Export issues to CSV
2. Use Summary → Task
3. Use Start Date → Start
4. Use Due Date → End
5. Use Status → Status

**From Excel:**
1. Save worksheet as CSV
2. Ensure column names match
3. Format dates consistently
4. Load in pandastable

---

## Quick Reference

### Minimum Required CSV

```csv
Task,Start,End
Task 1,2025-01-01,2025-01-10
Task 2,2025-01-05,2025-01-15
Task 3,2025-01-10,2025-01-20
```

### Full-Featured CSV

```csv
Task,Start,End,Duration,Progress,Status,Phase,Owner
Task 1,2025-01-01,2025-01-10,10,100,Complete,Phase 1,Alice
Task 2,2025-01-05,2025-01-15,10,75,In Progress,Phase 1,Bob
Task 3,2025-01-10,2025-01-20,10,50,In Progress,Phase 2,Alice
```

### Common Date Formats

| Input Format | Example | Parsed As |
|--------------|---------|-----------|
| YYYY-MM-DD | 2025-01-15 | Jan 15, 2025 |
| MM/DD/YYYY | 01/15/2025 | Jan 15, 2025 |
| DD/MM/YYYY | 15/01/2025 | Jan 15, 2025 |
| YYYY-MM-DD HH:MM | 2025-01-15 09:00 | Jan 15, 2025 9:00 AM |

---

## Summary Checklist

### To Create a Gantt Chart:

- [ ] Prepare CSV with Task and Start columns
- [ ] Add End or Duration column
- [ ] (Optional) Add Progress, Status, Phase columns
- [ ] Load CSV in pandastable
- [ ] Click Plot button
- [ ] Select 'gantt' plot type
- [ ] Configure options (progress, today line, etc.)
- [ ] Click "Apply Options"
- [ ] Review and adjust as needed

### For Best Results:

- [ ] Use consistent date format (YYYY-MM-DD recommended)
- [ ] Keep task names concise
- [ ] Update progress regularly
- [ ] Use meaningful status values
- [ ] Group related tasks
- [ ] Limit to 20-30 tasks per chart
- [ ] Include today's date in timeline

---

## File Locations

```
pandastable0/
├── pandastable/
│   └── plotting.py                 # Gantt chart implementation
├── examples/
│   └── csv_browser_v6.x1.2_search_columns.py  # CSV Browser
├── gantt_example_1_simple.csv      # Simple project example
├── gantt_example_2_duration.csv    # Duration-based example
├── gantt_example_3_phases.csv      # Multi-phase project example
└── GANTT_CHART_GUIDE.md            # This file
```

---

**Last Updated:** 2025-10-05  
**Version:** 1.0  
**Status:** ✅ Complete and Ready to Use
