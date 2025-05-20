from django.db import models


class Course(models.Model):
    name = models.TextField()
    target_score = models.IntegerField(default=0)

    class Meta:
        db_table = 'Course'

    def __str__(self):
        return f"Курс на {self.target_score} баллов"


class Section(models.Model):
    name = models.CharField(max_length=255)
    max_score = models.PositiveIntegerField(
        default=0,
        help_text="Максимальное число первичных баллов за раздел на ЕГЭ"
    )

    class Meta:
        db_table = 'Section'

    def __str__(self):
        return self.name


class CourseSection(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='course_sections'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='course_sections'
    )

    class Meta:
        db_table = 'Course_section'
        unique_together = ('course', 'section')

    def __str__(self):
        return f"{self.course} → {self.section}"
