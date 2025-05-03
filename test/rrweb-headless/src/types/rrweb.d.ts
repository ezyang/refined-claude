declare module 'rrweb/dist/types/types' {
  export interface eventWithTime {
    type: number;
    data: any;
    timestamp: number;
    delay?: number;
  }
}

declare module 'rrweb-player' {
  export default class Replayer {
    constructor(events: any[], options: any);
    play(): void;
    pause(): void;
    getCurrentTime(): number;
    getMetaData(): { totalTime: number };
  }
}

declare module 'rrweb' {
  import { eventWithTime } from 'rrweb/dist/types/types';
  export { eventWithTime };

  export class Replayer {
    constructor(events: eventWithTime[], options: any);
    play(): void;
    pause(): void;
    getCurrentTime(): number;
    getMetaData(): { totalTime: number };
  }
}
