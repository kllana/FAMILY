# statistics.py
import matplotlib.pyplot as plt

def show_statistics(world):
    time_data = list(range(len(world.pop_hist)))
    pop_data = list(world.pop_hist)
    capital_data = list(world.cap_hist)
    work_data = list(world.work_hist)
    working_ratio = world.get_working_ratio() if world.get_population() > 0 else 0
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Статистика модели семьи', fontsize=14)
    axes[0, 0].plot(time_data, pop_data, color='#4488ff')
    axes[0, 0].set_title('Изменение количества семей во времени')
    axes[0, 0].set_xlabel('Шаг времени')
    axes[0, 0].set_ylabel('Число семей')
    axes[0, 1].plot(time_data, capital_data, color='#4CAF50')
    axes[0, 1].set_title('Динамика среднего капитала семьи')
    axes[0, 1].set_xlabel('Шаг времени')
    axes[0, 1].set_ylabel('Капитал')
    axes[1, 0].plot(time_data, work_data, color='#FF9800')
    axes[1, 0].set_title('Доля работающих женщин')
    axes[1, 0].set_xlabel('Шаг времени')
    axes[1, 0].set_ylabel('Доля')
    working = int(working_ratio * world.get_population())
    non_working = world.get_population() - working
    bars = axes[1, 1].bar(['Работающие\nженщины', 'Неработающие\nженщины'],
                          [working, non_working],
                          color=['#4CAF50', '#FF9800'])
    axes[1, 1].set_title('Соотношение семей по идентичности женщин (текущее)')
    axes[1, 1].set_ylabel('Количество семей')
    for bar, val in zip(bars, [working, non_working]):
        if val > 0:
            axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                            str(val), ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.show(block=True)
