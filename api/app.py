# This program is free software: you can redistribute it and/or modify
# This is an API for pvpccheap program

from flask import Flask, render_template, request, jsonify
import pvpccheap.secrets as secrets
from pvpccheap.pvpccheap import ElectricPriceChecker, update_cheap_hours, Logger,  DateTimeHelper


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get-cheapest-hours', methods=['POST'])
def get_cheapest_hours():
    # This function get the cheapest hours for the current day
    max_hours = 6
    current_day, current_time, current_week_day = datetime_helper.get_dates()
    cheap_hours = update_cheap_hours(electric_price_checker, max_hours, current_day, logger)
    return jsonify(cheap_hours)


def initialize_app():
    # Initialize logger
    init_logger = Logger()

    # Initialize DateTimeHelper and ElectricPriceChecker
    init_electric_price_checker = ElectricPriceChecker(secrets, 'Europe/Madrid', logger)
    init_datetime_helper = DateTimeHelper('Europe/Madrid', logger)

    return init_logger, init_electric_price_checker, init_datetime_helper


if __name__ == '__main__':
    logger, electric_price_checker, datetime_helper = initialize_app()

    app.run(debug=True)