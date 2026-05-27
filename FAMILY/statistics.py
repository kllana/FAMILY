import matplotlib.pyplot as plt

def show_statistics(world):
    time_data = list(range(len(world.pop_hist)))
    pop_data = list(world.pop_hist)
    capital_data = list(world.cap_hist)
    work_data = list(world.work_hist)
    working_ratio = world.get_working_ratio() if world.get_population() > 0 else 0

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Статистика модели семьи', fontsize=12)

    axes[0, 0].plot(time_data, pop_data, color='#4488ff', linewidth=1.5)
    axes[0, 0].set_title('Численность семей', fontsize=10)
    axes[0, 0].set_xlabel('Шаг времени', fontsize=8)
    axes[0, 0].set_ylabel('Количество семей', fontsize=8)
    axes[0, 0].tick_params(labelsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(time_data, capital_data, color='#4CAF50', linewidth=1.5)
    axes[0, 1].set_title('Средний капитал семьи', fontsize=10)
    axes[0, 1].set_xlabel('Шаг времени', fontsize=8)
    axes[0, 1].set_ylabel('Капитал', fontsize=8)
    axes[0, 1].tick_params(labelsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(time_data, work_data, color='#FF9800', linewidth=1.5)
    axes[1, 0].set_title('Доля работающих женщин', fontsize=10)
    axes[1, 0].set_xlabel('Шаг времени', fontsize=8)
    axes[1, 0].set_ylabel('Доля', fontsize=8)
    axes[1, 0].tick_params(labelsize=8)
    axes[1, 0].grid(True, alpha=0.3)

    working = int(working_ratio * world.get_population())
    non_working = world.get_population() - working
    bars = axes[1, 1].bar(['Работающие\nженщины', 'Неработающие\nженщины'],
                          [working, non_working],
                          color=['#4CAF50', '#FF9800'])
    axes[1, 1].set_title('Идентичность женщин (текущее)', fontsize=10)
    axes[1, 1].set_ylabel('Количество семей', fontsize=8)
    axes[1, 1].tick_params(labelsize=8)
    axes[1, 1].set_ylim(0, max(working, non_working) * 1.2 if (working + non_working) > 0 else 1)

    for bar, val in zip(bars, [working, non_working]):
        if val > 0:
            axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                            str(val), ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.show(block=True)