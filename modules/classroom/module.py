"""
modules.classroom.module
============================

Classroom — v1 (2026-09-11): the user's own self-education content
model, Subjects -> Courses -> Lessons, three-level drill-down navigation
(same "list page + a QStackedWidget page per level, '<- Back' to go up"
shape as modules/real_estate/module.py). Deliberately just the content/
lesson structure this pass — no Skills/Missions/Discovery wiring yet;
see core/classroom_manager.py's own docstring for what's not built.

format_subject_row()/format_course_row()/format_lesson_row() are free
functions (not methods) — testable without Qt, see
tests/test_classroom_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.classroom_manager import Course, Lesson, Subject
from gui.add_edit_classroom_course_dialog import AddEditCourseDialog
from gui.add_edit_classroom_lesson_dialog import AddEditLessonDialog
from gui.add_edit_classroom_subject_dialog import AddEditSubjectDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from modules.module_base import ModuleBase


def format_completion_summary(done: int, total: int) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{done} of {total} complete" if total else "No lessons yet"


def format_subject_row(subject: Subject, done: int, total: int) -> str:
    """Pure formatting logic — testable without Qt."""
    suffix = f" [{subject.category}]" if subject.category else ""
    return f"{subject.name}{suffix} — {format_completion_summary(done, total)}"


def format_course_row(course: Course, done: int, total: int) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{course.name} — {format_completion_summary(done, total)}"


def format_lesson_row(lesson: Lesson) -> str:
    """Pure formatting logic — testable without Qt."""
    marker = "✓" if lesson.completed else "○"
    return f"{marker} {lesson.name}"


class ClassroomModule(ModuleBase):
    module_id = "classroom"
    display_name = "Classroom"
    description = "Your own subjects, courses, and lessons."
    icon = "\U0001F393"  # graduation cap

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stack: Optional[QStackedWidget] = None
        self._subjects_page: Optional[QWidget] = None
        self._courses_page: Optional[QWidget] = None
        self._lessons_page: Optional[QWidget] = None

        self._subject_list: Optional[QListWidget] = None
        self._course_list: Optional[QListWidget] = None
        self._lesson_list: Optional[QListWidget] = None
        self._course_list_title: Optional[QLabel] = None
        self._lesson_list_title: Optional[QLabel] = None

        self._current_subject_id: Optional[str] = None
        self._current_course_id: Optional[str] = None

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_subject_list()

    def get_widget(self) -> QWidget:
        self._stack = QStackedWidget()
        self._subjects_page = self._build_subjects_page()
        self._stack.addWidget(self._subjects_page)
        self._stack.setCurrentWidget(self._subjects_page)
        return self._stack

    # ------------------------------------------------------------------
    # Subjects (top level)
    # ------------------------------------------------------------------

    def _build_subjects_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        self._subject_list = QListWidget()
        self._subject_list.itemDoubleClicked.connect(lambda _item: self._on_open_subject())
        layout.addWidget(self._subject_list, stretch=1)

        buttons = QHBoxLayout()
        add_button = QPushButton("Add Subject")
        add_button.clicked.connect(self._on_add_subject)
        buttons.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_subject)
        buttons.addWidget(edit_button)

        open_button = QPushButton("Open")
        open_button.clicked.connect(self._on_open_subject)
        buttons.addWidget(open_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_subject)
        buttons.addWidget(delete_button)

        layout.addLayout(buttons)

        # Textbook tutor (2026-09-28): the owner's books, a page of its own.
        if self.context.textbooks is not None:
            textbooks_button = QPushButton("\U0001F4DA  Textbooks")
            textbooks_button.clicked.connect(self._on_open_textbooks)
            layout.addWidget(textbooks_button)

        self._refresh_subject_list()
        return page

    def _on_open_textbooks(self) -> None:
        from gui.textbooks_panel import TextbooksPanel

        if getattr(self, "_textbooks_page", None) is None:
            self._textbooks_page = TextbooksPanel(self.context, on_back=self._back_from_textbooks)
            self._stack.addWidget(self._textbooks_page)
        self._textbooks_page.refresh()
        self._stack.setCurrentWidget(self._textbooks_page)

    def _back_from_textbooks(self) -> None:
        self._refresh_subject_list()  # a course may have been made
        self._stack.setCurrentWidget(self._subjects_page)

    def _refresh_subject_list(self) -> None:
        self._subject_list.clear()
        subjects = self.context.classroom.all_subjects()
        for subject in subjects:
            done, total = self.context.classroom.subject_completion(subject.subject_id)
            item = QListWidgetItem(format_subject_row(subject, done, total))
            item.setData(Qt.ItemDataRole.UserRole, subject.subject_id)
            self._subject_list.addItem(item)
        if not subjects:
            add_empty_state_item(self._subject_list, "No subjects yet — click Add Subject to get started.")

    def _selected_subject_id(self) -> Optional[str]:
        return selected_item_data(self._subject_list)

    def _on_add_subject(self) -> None:
        dialog = AddEditSubjectDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.add_subject(
            name=dialog.entered_name, category=dialog.entered_category, description=dialog.entered_description,
        )
        self._refresh_subject_list()

    def _on_edit_subject(self) -> None:
        subject_id = self._selected_subject_id()
        if subject_id is None:
            QMessageBox.information(None, "No Subject Selected", "Select a subject to edit.")
            return
        subject = self.context.classroom.get_subject(subject_id)
        dialog = AddEditSubjectDialog(self.context, subject=subject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.update_subject(
            subject_id, name=dialog.entered_name, category=dialog.entered_category,
            description=dialog.entered_description,
        )
        self._refresh_subject_list()

    def _on_delete_subject(self) -> None:
        subject_id = self._selected_subject_id()
        if subject_id is None:
            QMessageBox.information(None, "No Subject Selected", "Select a subject to delete.")
            return
        subject = self.context.classroom.get_subject(subject_id)
        confirm = QMessageBox.question(
            None, "Delete Subject",
            f"Delete '{subject.name}'? This also deletes all of its Courses and Lessons.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.classroom.delete_subject(subject_id)
        self._refresh_subject_list()

    def _on_open_subject(self) -> None:
        subject_id = self._selected_subject_id()
        if subject_id is None:
            QMessageBox.information(None, "No Subject Selected", "Select a subject to open.")
            return
        self._show_courses_page(subject_id)

    # ------------------------------------------------------------------
    # Courses (within a Subject)
    # ------------------------------------------------------------------

    def _show_courses_page(self, subject_id: str) -> None:
        if self._courses_page is not None:
            self._stack.removeWidget(self._courses_page)
            self._courses_page = None
        self._current_subject_id = subject_id
        self._courses_page = self._build_courses_page()
        self._stack.addWidget(self._courses_page)
        self._stack.setCurrentWidget(self._courses_page)

    def _build_courses_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        back_button = QPushButton("← Back to Subjects")
        back_button.clicked.connect(self._show_subjects_page)
        layout.addWidget(back_button)

        subject = self.context.classroom.get_subject(self._current_subject_id)
        self._course_list_title = QLabel(subject.name if subject else "")
        self._course_list_title.setObjectName("TitleLabel")
        layout.addWidget(self._course_list_title)

        self._course_list = QListWidget()
        self._course_list.itemDoubleClicked.connect(lambda _item: self._on_open_course())
        layout.addWidget(self._course_list, stretch=1)

        buttons = QHBoxLayout()
        add_button = QPushButton("Add Course")
        add_button.clicked.connect(self._on_add_course)
        buttons.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_course)
        buttons.addWidget(edit_button)

        open_button = QPushButton("Open")
        open_button.clicked.connect(self._on_open_course)
        buttons.addWidget(open_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_course)
        buttons.addWidget(delete_button)

        layout.addLayout(buttons)

        self._refresh_course_list()
        return page

    def _refresh_course_list(self) -> None:
        self._course_list.clear()
        courses = self.context.classroom.courses_for_subject(self._current_subject_id)
        for course in courses:
            done, total = self.context.classroom.course_completion(course.course_id)
            item = QListWidgetItem(format_course_row(course, done, total))
            item.setData(Qt.ItemDataRole.UserRole, course.course_id)
            self._course_list.addItem(item)
        if not courses:
            add_empty_state_item(self._course_list, "No courses yet — click Add Course to get started.")

    def _selected_course_id(self) -> Optional[str]:
        return selected_item_data(self._course_list)

    def _on_add_course(self) -> None:
        dialog = AddEditCourseDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.add_course(
            subject_id=self._current_subject_id, name=dialog.entered_name, description=dialog.entered_description,
        )
        self._refresh_course_list()

    def _on_edit_course(self) -> None:
        course_id = self._selected_course_id()
        if course_id is None:
            QMessageBox.information(None, "No Course Selected", "Select a course to edit.")
            return
        course = self.context.classroom.get_course(course_id)
        dialog = AddEditCourseDialog(self.context, course=course)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.update_course(
            course_id, name=dialog.entered_name, description=dialog.entered_description,
        )
        self._refresh_course_list()

    def _on_delete_course(self) -> None:
        course_id = self._selected_course_id()
        if course_id is None:
            QMessageBox.information(None, "No Course Selected", "Select a course to delete.")
            return
        course = self.context.classroom.get_course(course_id)
        confirm = QMessageBox.question(
            None, "Delete Course", f"Delete '{course.name}'? This also deletes all of its Lessons.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.classroom.delete_course(course_id)
        self._refresh_course_list()

    def _on_open_course(self) -> None:
        course_id = self._selected_course_id()
        if course_id is None:
            QMessageBox.information(None, "No Course Selected", "Select a course to open.")
            return
        self._show_lessons_page(course_id)

    def _show_subjects_page(self) -> None:
        self._stack.setCurrentWidget(self._subjects_page)
        if self._courses_page is not None:
            self._stack.removeWidget(self._courses_page)
            self._courses_page = None
        if self._lessons_page is not None:
            self._stack.removeWidget(self._lessons_page)
            self._lessons_page = None
        self._current_subject_id = None
        self._current_course_id = None
        self._refresh_subject_list()

    # ------------------------------------------------------------------
    # Lessons (within a Course)
    # ------------------------------------------------------------------

    def _show_lessons_page(self, course_id: str) -> None:
        if self._lessons_page is not None:
            self._stack.removeWidget(self._lessons_page)
            self._lessons_page = None
        self._current_course_id = course_id
        self._lessons_page = self._build_lessons_page()
        self._stack.addWidget(self._lessons_page)
        self._stack.setCurrentWidget(self._lessons_page)

    def _build_lessons_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        back_button = QPushButton("← Back to Courses")
        back_button.clicked.connect(self._show_courses_page_from_lessons)
        layout.addWidget(back_button)

        course = self.context.classroom.get_course(self._current_course_id)
        self._lesson_list_title = QLabel(course.name if course else "")
        self._lesson_list_title.setObjectName("TitleLabel")
        layout.addWidget(self._lesson_list_title)

        self._lesson_list = QListWidget()
        layout.addWidget(self._lesson_list, stretch=1)

        buttons = QHBoxLayout()
        add_button = QPushButton("Add Lesson")
        add_button.clicked.connect(self._on_add_lesson)
        buttons.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_lesson)
        buttons.addWidget(edit_button)

        toggle_button = QPushButton("Mark Complete/Incomplete")
        toggle_button.clicked.connect(self._on_toggle_lesson_complete)
        buttons.addWidget(toggle_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_lesson)
        buttons.addWidget(delete_button)

        layout.addLayout(buttons)

        self._refresh_lesson_list()
        return page

    def _refresh_lesson_list(self) -> None:
        self._lesson_list.clear()
        lessons = self.context.classroom.lessons_for_course(self._current_course_id)
        for lesson in lessons:
            item = QListWidgetItem(format_lesson_row(lesson))
            item.setData(Qt.ItemDataRole.UserRole, lesson.lesson_id)
            self._lesson_list.addItem(item)
        if not lessons:
            add_empty_state_item(self._lesson_list, "No lessons yet — click Add Lesson to get started.")

    def _selected_lesson_id(self) -> Optional[str]:
        return selected_item_data(self._lesson_list)

    def _on_add_lesson(self) -> None:
        dialog = AddEditLessonDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.add_lesson(
            course_id=self._current_course_id, name=dialog.entered_name, notes=dialog.entered_notes,
            skill_rewards=dialog.entered_skill_rewards,
        )
        self._refresh_lesson_list()

    def _on_edit_lesson(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            QMessageBox.information(None, "No Lesson Selected", "Select a lesson to edit.")
            return
        lesson = self.context.classroom.get_lesson(lesson_id)
        dialog = AddEditLessonDialog(self.context, lesson=lesson)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.classroom.update_lesson(
            lesson_id, name=dialog.entered_name, notes=dialog.entered_notes,
            skill_rewards=dialog.entered_skill_rewards,
        )
        self._refresh_lesson_list()

    def _on_toggle_lesson_complete(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            QMessageBox.information(None, "No Lesson Selected", "Select a lesson to mark complete/incomplete.")
            return
        lesson = self.context.classroom.get_lesson(lesson_id)
        self.context.classroom.update_lesson(lesson_id, completed=not lesson.completed)
        self._refresh_lesson_list()

    def _on_delete_lesson(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            QMessageBox.information(None, "No Lesson Selected", "Select a lesson to delete.")
            return
        lesson = self.context.classroom.get_lesson(lesson_id)
        confirm = QMessageBox.question(
            None, "Delete Lesson", f"Delete '{lesson.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.classroom.delete_lesson(lesson_id)
        self._refresh_lesson_list()

    def _show_courses_page_from_lessons(self) -> None:
        self._stack.setCurrentWidget(self._courses_page)
        if self._lessons_page is not None:
            self._stack.removeWidget(self._lessons_page)
            self._lessons_page = None
        self._current_course_id = None
        self._refresh_course_list()
