---
id: K-0089
kind: implementation
title: Projects page and the None due date
status: confirmed
by: claude
created: 2026-11-08T01:45:45+00:00
concerns: core/web_projects.py, core/project_manager.py, web/projects.js, core/more_actions.py
from: commit:25f625f, dec:DEC-0125
---
web/projects.html shows core.project_manager projects (homestead builds like a greenhouse) with homestead_costs.build_cost money and core.task_manager tasks; project.add/edit/delete come from the shared record table (more_actions RECORDS["project"], budget left out because add_project takes none, so project.budget sets it). What went wrong: a blank date from the record form is saved as None, and ProjectManager.all_projects sorted on (due == "", due), which cannot compare None with a string; the sort now treats a missing date as blank. Deleting a project keeps its task records, the same as the voice tool.
