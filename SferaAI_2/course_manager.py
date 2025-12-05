import json
import os
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CourseManager:
    def __init__(self, curriculum_path: str = "data/courses/master_curriculum.json"):
        self.curriculum_path = curriculum_path
        self.courses = {}
        self.lessons_map = {}  # Map lesson_id to lesson data
        self.user_progress = {}  # Map user_id to current_lesson_id
        self._load_curriculum()

    def _load_curriculum(self):
        """Loads the master curriculum JSON file."""
        try:
            if not os.path.exists(self.curriculum_path):
                logger.error(f"Curriculum file not found: {self.curriculum_path}")
                return

            with open(self.curriculum_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for course in data.get('courses', []):
                self.courses[course['id']] = course
                for module in course.get('modules', []):
                    for lesson in module.get('lessons', []):
                        # Store full lesson metadata
                        self.lessons_map[lesson['id']] = {
                            **lesson,
                            "course_id": course['id'],
                            "module_id": module['id']
                        }
            logger.info(f"Loaded {len(self.courses)} courses and {len(self.lessons_map)} lessons.")
            
        except Exception as e:
            logger.error(f"Failed to load curriculum: {e}")

    def get_course_list(self) -> List[Dict[str, Any]]:
        """Returns a list of available courses."""
        return [{"id": c['id'], "title": c['title'], "description": c['description']} for c in self.courses.values()]

    def start_course(self, user_id: str, course_id: str) -> Optional[str]:
        """Starts a course for a user. Returns the first lesson ID."""
        if course_id not in self.courses:
            return None
        
        # Find the first lesson of the first module
        course = self.courses[course_id]
        if not course['modules'] or not course['modules'][0]['lessons']:
            return None
            
        first_lesson_id = course['modules'][0]['lessons'][0]['id']
        self.user_progress[user_id] = {
            "course_id": course_id,
            "current_lesson_id": first_lesson_id,
            "completed_lessons": []
        }
        return first_lesson_id

    def get_current_lesson(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns the metadata of the user's current lesson."""
        progress = self.user_progress.get(user_id)
        if not progress:
            return None
        return self.lessons_map.get(progress['current_lesson_id'])

    def get_lesson_content(self, lesson_id: str) -> Dict[str, Any]:
        """
        Reads and parses the lesson markdown file.
        Returns a dict with: theory, image_url, task, quiz.
        """
        lesson_meta = self.lessons_map.get(lesson_id)
        if not lesson_meta:
            return {"error": "Lesson not found"}

        file_path = lesson_meta.get('file_path')
        if not os.path.exists(file_path):
            return {"error": f"Lesson file not found: {file_path}"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple parsing logic based on headers
            sections = {
                "theory": "",
                "image": None,
                "task": "",
                "quiz": ""
            }
            
            current_section = None
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("## 📚 Теория"):
                    current_section = "theory"
                    continue
                elif stripped.startswith("## 🖼️ Визуальные материалы"):
                    current_section = "image_section"
                    continue
                elif stripped.startswith("## 🏋️‍♂️ Практическое Задание"):
                    current_section = "task"
                    continue
                elif stripped.startswith("## ❓ Проверочный Вопрос"):
                    current_section = "quiz"
                    continue
                elif stripped.startswith("# "): # Title
                    continue
                
                # Content extraction
                if current_section == "theory":
                    sections["theory"] += line + "\n"
                elif current_section == "image_section":
                    if stripped.startswith("**Image:**"):
                        # Extract URL: **Image:** /path/to/img.png
                        sections["image"] = stripped.replace("**Image:**", "").strip().strip('`')
                elif current_section == "task":
                    sections["task"] += line + "\n"
                elif current_section == "quiz":
                    sections["quiz"] += line + "\n"

            return {
                "id": lesson_id,
                "title": lesson_meta['title'],
                "theory": sections["theory"].strip(),
                "image_url": sections["image"],
                "task": sections["task"].strip(),
                "quiz": sections["quiz"].strip()
            }

        except Exception as e:
            logger.error(f"Error reading lesson file: {e}")
            return {"error": str(e)}

    def complete_lesson(self, user_id: str):
        """Marks the current lesson as complete and moves to the next one."""
        progress = self.user_progress.get(user_id)
        if not progress:
            return None

        current_id = progress['current_lesson_id']
        progress['completed_lessons'].append(current_id)
        
        # Find next lesson
        # This is a simplified linear search. In a real app, we'd use a linked list or index.
        course = self.courses[progress['course_id']]
        found_current = False
        next_lesson_id = None
        
        for module in course['modules']:
            for lesson in module['lessons']:
                if found_current:
                    next_lesson_id = lesson['id']
                    break
                if lesson['id'] == current_id:
                    found_current = True
            if next_lesson_id:
                break
        
        if next_lesson_id:
            progress['current_lesson_id'] = next_lesson_id
            return next_lesson_id
        else:
            return "COURSE_COMPLETED"

# Singleton instance for easy import
course_manager = CourseManager()
