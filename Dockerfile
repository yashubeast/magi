FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git

RUN git clone https://github.com/yashubeast/magi.git . && \
	npm install --production

EXPOSE 8000

CMD ["node", "app.js"]

