from pydantic import BaseModel


class AnswerStat(BaseModel):
    value: str
    unit: str
    context: str
    source: str
    page: int = 0


class AnswerChartBar(BaseModel):
    label: str
    value: float
    highlight: bool = False


class AnswerChart(BaseModel):
    title: str
    source: str
    unit: str
    bars: list[AnswerChartBar]


class StructuredAnswer(BaseModel):
    summary: list[str]
    stats: list[AnswerStat] = []
    chart: AnswerChart | None = None
    checklist: list[str] | None = None
    followups: list[str] = []
