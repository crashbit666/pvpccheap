const devices = document.querySelectorAll('.device');

devices.forEach((device) => {
  const sleepBars = device.querySelectorAll('.sleep-bar');

  sleepBars.forEach((sleepBar) => {
    const sleepHours = Array.from(sleepBar.querySelectorAll('.sleep-hour'));
    const hourLabels = Array.from(sleepBar.querySelectorAll('.hour-label'));
    const activeHours = sleepHours.filter((hour) => hour.classList.contains('active'));

    activeHours.forEach((hour) => {
      const hourIndex = sleepHours.indexOf(hour);
      const hourLabel = hourLabels[hourIndex];
      hourLabel.classList.add('active-hour-label');
      hourLabel.style.color = 'red';
    });
  });
});

