# This program is free software: you can redistribute it and/or modify
# This is an API for pvpccheap program

from flask import Flask,  jsonify
from flask_restful import Api, Resource
from pvpccheap.secrets import secrets
from pvpccheap.pvpccheap import ElectricPriceChecker, update_cheap_hours, Logger,  DateTimeHelper


app = Flask(__name__)
api = Api(app)


class CheapestHours(Resource):
    def __init__(self):
        # Initialize logger
        self.logger = Logger()

        # Initialize DateTimeHelper and ElectricPriceChecker
        self.electric_price_checker = ElectricPriceChecker(secrets, 'Europe/Madrid', self.logger)
        self.datetime_helper = DateTimeHelper('Europe/Madrid', self.logger)

    def get(self):
        # Get cheap hours
        current_day, current_time, current_week_day = self.datetime_helper.get_dates()
        cheap_hours = update_cheap_hours(self.electric_price_checker, current_day, self.logger)

        return jsonify({"cheapest_hours": cheap_hours})


api.add_resource(CheapestHours, '/cheapest-hours', endpoint='cheapest-hours')


if __name__ == '__main__':
    app.run(debug=True)
